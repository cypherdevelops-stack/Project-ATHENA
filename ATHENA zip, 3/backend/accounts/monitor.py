from __future__ import annotations

import os
import subprocess
import threading
import time

from django.db import close_old_connections
from django.utils import timezone

from .credentials import decrypt_password
from .handshake import DEFAULT_MT5_TERMINAL_PATH
from .models import Account

CHECK_INTERVAL_SECONDS = 2
_monitor_started = False
_monitor_lock = threading.Lock()


def normalize_terminal_path(path: str) -> str:
    return str(path or '').strip().strip('"')


def _load_mt5():
    try:
        import MetaTrader5 as mt5
    except Exception:
        return None
    return mt5


def _launch_terminal(path: str) -> bool:
    path = normalize_terminal_path(path)
    if not path or not os.path.exists(path):
        return False
    try:
        subprocess.Popen([path], close_fds=True)
    except OSError:
        return False
    return True


def terminal_process_running() -> bool:
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq terminal64.exe', '/FO', 'CSV', '/NH'],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return 'terminal64.exe' in result.stdout.lower()


def check_account(account: Account) -> None:
    if not account.enabled:
        return
    mt5 = _load_mt5()
    if mt5 is None:
        Account.objects.filter(pk=account.pk).update(
            terminal_connected=False,
            handshake_status='MT5_UNAVAILABLE',
        )
        return

    path = normalize_terminal_path(account.terminal_path or DEFAULT_MT5_TERMINAL_PATH)
    if not terminal_process_running():
        launched = _launch_terminal(path)
        Account.objects.filter(pk=account.pk).update(
            terminal_connected=False,
            trade_allowed=False,
            handshake_status='RECONNECTING' if launched else 'RECONNECT_FAILED',
        )
        return
    password = None
    try:
        password = decrypt_password(account.password_encrypted)
    except Exception:
        Account.objects.filter(pk=account.pk).update(
            terminal_connected=False,
            handshake_status='CREDENTIALS_UNAVAILABLE',
        )
        return

    initialized = False
    try:
        initialized = mt5.initialize(path=path)
        if not initialized:
            launched = _launch_terminal(path)
            Account.objects.filter(pk=account.pk).update(
                terminal_connected=False,
                trade_allowed=False,
                handshake_status='RECONNECTING' if launched else 'RECONNECT_FAILED',
            )
            return
        if not mt5.login(login=int(account.login), password=password, server=account.server):
            Account.objects.filter(pk=account.pk).update(
                terminal_connected=True,
                trade_allowed=False,
                handshake_status='AUTH_FAILED',
            )
            return
        account_info = mt5.account_info()
        if account_info is None:
            Account.objects.filter(pk=account.pk).update(
                terminal_connected=True,
                trade_allowed=False,
                handshake_status='TELEMETRY_FAILED',
            )
            return
        Account.objects.filter(pk=account.pk).update(
            terminal_connected=True,
            trade_allowed=bool(getattr(account_info, 'trade_allowed', False)),
            balance=getattr(account_info, 'balance', account.balance),
            equity=getattr(account_info, 'equity', account.equity),
            account_mode=str(getattr(account_info, 'trade_mode', account.account_mode)),
            last_handshake_at=timezone.now(),
            handshake_status='CONNECTED',
        )
    except (TypeError, ValueError, OSError):
        Account.objects.filter(pk=account.pk).update(
            terminal_connected=False,
            handshake_status='RECONNECT_FAILED',
        )
    finally:
        if initialized:
            mt5.shutdown()


def monitor_loop() -> None:
    while True:
        close_old_connections()
        for account in Account.objects.filter(enabled=True).iterator():
            check_account(account)
        close_old_connections()
        time.sleep(CHECK_INTERVAL_SECONDS)


def start_monitor() -> None:
    global _monitor_started
    with _monitor_lock:
        if _monitor_started:
            return
        if 'test' in os.sys.argv or os.environ.get('ATHENA_DISABLE_MT5_MONITOR') == '1':
            return
        thread = threading.Thread(target=monitor_loop, name='athena-mt5-monitor', daemon=True)
        thread.start()
        _monitor_started = True
