from __future__ import annotations

import csv
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone


_CSV_LOCK = threading.Lock()
_FIELDS = (
    'timestamp',
    'account_id',
    'symbol',
    'strategy',
    'decision_id',
    'candidate_id',
    'signal',
    'decision_state',
    'score',
    'entry_zone',
    'candidate',
    'executed',
    'execution_status',
    'reason',
)


def _audit_directory() -> Path:
    return Path(getattr(
        settings,
        'TRADING_AUDIT_DIR',
        Path(settings.BASE_DIR) / 'logs' / 'trading',
    ))


def _csv_path(strategy: str, timestamp: datetime) -> Path:
    date = timezone.localtime(timestamp).date().isoformat()
    filename = 'daytrading' if strategy == 'DAY_TRADING' else 'scalping'
    return _audit_directory() / f'{filename}_{date}.csv'


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(',', ':'))


def record_orchestration_candidates(
    *,
    account,
    analysis: dict[str, Any],
    decision_id,
    timestamp: datetime | None = None,
) -> None:
    """Append every detected candidate and its current orchestration disposition."""
    timestamp = timestamp or timezone.now()
    orchestration = analysis.get('orchestration') or {}
    decision = orchestration.get('decision') or {}
    selected_strategy = decision.get('strategy')
    action = decision.get('action', orchestration.get('status', 'OBSERVE'))
    approved = action.endswith('_APPROVED')
    decision_reason = decision.get('reason') or orchestration.get('reason', '')
    decision_reason_codes = decision.get('reasonCodes') or []
    portfolio_blocked = any(code != 'NO_READY_CANDIDATE' for code in decision_reason_codes)

    strategy_sources = (
        ('SCALPING', 'scalping'),
        ('DAY_TRADING', 'dayTrading'),
    )
    rows_by_path: dict[Path, list[dict[str, Any]]] = {}
    for strategy, key in strategy_sources:
        candidates = ((analysis.get(key) or {}).get('candidates') or [])
        for candidate in candidates:
            is_selected = approved and selected_strategy == strategy
            candidate_reasons = candidate.get('reasonCodes') or []
            if is_selected:
                executed = 'PENDING'
                execution_status = 'QUEUED'
                reason = 'Selected for execution; waiting for the execution result.'
            else:
                executed = 'NO'
                execution_status = 'NOT_EXECUTED'
                if decision_reason and (selected_strategy == strategy or portfolio_blocked):
                    reason = decision_reason
                elif candidate_reasons:
                    reason = ', '.join(candidate_reasons)
                else:
                    reason = f'{strategy.replace("_", " ").title()} candidate was not selected for execution.'
            path = _csv_path(strategy, timestamp)
            rows_by_path.setdefault(path, []).append({
                'timestamp': timestamp.isoformat(),
                'account_id': account.pk,
                'symbol': account.broker_symbol or account.canonical_asset or '',
                'strategy': strategy,
                'decision_id': str(decision_id),
                'candidate_id': candidate.get('candidateId', ''),
                'signal': candidate.get('direction') or 'NONE',
                'decision_state': candidate.get('decisionState', 'UNKNOWN'),
                'score': candidate.get('score', ''),
                'entry_zone': _json(candidate.get('entryZone')),
                'candidate': _json(candidate),
                'executed': executed,
                'execution_status': execution_status,
                'reason': reason,
            })

    with _CSV_LOCK:
        for path, rows in rows_by_path.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            write_header = not path.exists() or path.stat().st_size == 0
            with path.open('a', encoding='utf-8', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=_FIELDS)
                if write_header:
                    writer.writeheader()
                writer.writerows(rows)


def record_execution_outcome(
    *,
    strategy: str,
    decision_id,
    executed: bool,
    execution_status: str,
    reason: str,
    timestamp: datetime | None = None,
) -> None:
    """Update all candidate rows for a decision with its final execution outcome."""
    if strategy not in {'SCALPING', 'DAY_TRADING'}:
        return
    path = _csv_path(strategy, timestamp or timezone.now())
    with _CSV_LOCK:
        filename = 'daytrading' if strategy == 'DAY_TRADING' else 'scalping'
        other_daily_files = sorted(_audit_directory().glob(f'{filename}_*.csv'))
        paths = [path, *(daily_path for daily_path in other_daily_files if daily_path != path)]
        for daily_path in paths:
            if not daily_path.exists():
                continue
            with daily_path.open('r', encoding='utf-8', newline='') as csv_file:
                reader = csv.DictReader(csv_file)
                rows = list(reader)
                fieldnames = reader.fieldnames or list(_FIELDS)
            changed = False
            for row in rows:
                if row.get('decision_id') == str(decision_id):
                    row['executed'] = 'YES' if executed else 'NO'
                    row['execution_status'] = execution_status
                    row['reason'] = reason
                    changed = True
            if changed:
                with daily_path.open('w', encoding='utf-8', newline='') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                return
