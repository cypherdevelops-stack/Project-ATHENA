from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / '.env'
TERMINAL_PATH = Path(r'E:\Programs\Program Files (USB)\HFM Metatrader 5\terminal64.exe')


def fail(message: str) -> int:
    print(f'FAILED: {message}')
    return 1


def main() -> int:
    load_dotenv(ENV_FILE)

    login = os.getenv('login', '').strip()
    server = os.getenv('server', '').strip()
    password = os.getenv('password', '')

    if not login or not server or not password:
        return fail(f'Missing login, server, or password in {ENV_FILE}.')

    try:
        account_id = int(login)
    except ValueError:
        return fail('The login value in .env must be numeric.')

    if not TERMINAL_PATH.is_file():
        return fail(f'MT5 terminal was not found at {TERMINAL_PATH}.')

    try:
        import MetaTrader5 as mt5
    except Exception as error:
        if '_core' in str(error):
            return fail(
                'The installed MetaTrader5 native extension is incompatible with this Python interpreter. '
                'Use a Python 3.12 virtual environment and reinstall requirements.txt.'
            )
        return fail(f'Unable to import MetaTrader5: {error}')

    initialized = False
    try:
        print(f'Launching MT5 terminal: {TERMINAL_PATH}')
        initialized = mt5.initialize(path=str(TERMINAL_PATH))
        if not initialized:
            return fail(f'Terminal initialization failed: {mt5.last_error()}')

        print(f'Logging in to server: {server}')
        if not mt5.login(login=account_id, password=password, server=server):
            return fail(f'Broker login failed: {mt5.last_error()}')

        account_info = mt5.account_info()
        if account_info is None:
            return fail(f'Login succeeded, but account telemetry was unavailable: {mt5.last_error()}')

        print('SUCCESS: MT5 terminal initialized and broker login accepted.')
        print(f'  Account: {account_info.login}')
        print(f'  Broker: {account_info.company}')
        print(f'  Server: {account_info.server}')
        print(f'  Balance: {account_info.balance} {account_info.currency}')
        print(f'  Leverage: 1:{account_info.leverage}')
        print(f'  Trading allowed: {getattr(account_info, "trade_allowed", "unknown")}')
        return 0
    except Exception as error:
        return fail(f'MT5 runtime error: {error}')
    finally:
        if initialized:
            mt5.shutdown()


if __name__ == '__main__':
    sys.exit(main())
