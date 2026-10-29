from __future__ import annotations

import csv
import textwrap
from datetime import date
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from backend.accounts.models import Account
from backend.execution.trading_audit import _audit_directory


_STRATEGIES = {
    'day-trading': ('DAY_TRADING', 'daytrading'),
    'scalping': ('SCALPING', 'scalping'),
}


def _report_rows(request, strategy_slug: str, report_date: date) -> tuple[str, list[dict[str, str]]]:
    if strategy_slug not in _STRATEGIES:
        raise ValueError('Unknown strategy report.')
    strategy, filename = _STRATEGIES[strategy_slug]
    path = _audit_directory() / f'{filename}_{report_date.isoformat()}.csv'
    if not path.exists():
        return strategy, []
    account_ids = {
        str(account_id)
        for account_id in Account.objects.filter(user=request.user).values_list('pk', flat=True)
    }
    with path.open('r', encoding='utf-8', newline='') as csv_file:
        rows = list(csv.DictReader(csv_file))
    return strategy, [
        row for row in rows
        if row.get('strategy') == strategy and row.get('account_id') in account_ids
    ]


def _requested_date(request) -> date:
    value = request.GET.get('date')
    if not value:
        return timezone.localdate()
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError('date must use YYYY-MM-DD format.') from error


def _pdf_escape(value: str) -> str:
    safe = value.encode('latin-1', errors='replace').decode('latin-1')
    return safe.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _build_pdf(lines: list[str]) -> bytes:
    wrapped = [
        line
        for item in lines
        for line in (textwrap.wrap(item, width=92) or [''])
    ]
    page_lines = [wrapped[index:index + 52] for index in range(0, len(wrapped), 52)] or [[]]
    objects: list[bytes] = []
    page_ids = [4 + index * 2 for index in range(len(page_lines))]
    objects.append(b'<< /Type /Catalog /Pages 2 0 R >>')
    objects.append(
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>".encode('ascii')
    )
    objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    for index, content_lines in enumerate(page_lines):
        page_id = page_ids[index]
        content_id = page_id + 1
        commands = ['BT', '/F1 9 Tf', '50 760 Td', '12 TL']
        commands.extend(f'({_pdf_escape(line)}) Tj T*' for line in content_lines)
        commands.append('ET')
        stream = '\n'.join(commands).encode('latin-1')
        objects.append(
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            f'/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode('ascii')
        )
        objects.append(b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n' + stream + b'\nendstream')

    document = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f'{index} 0 obj\n'.encode('ascii'))
        document.extend(item)
        document.extend(b'\nendobj\n')
    xref_offset = len(document)
    document.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
    document.extend(b'0000000000 65535 f \n')
    document.extend(b''.join(f'{offset:010d} 00000 n \n'.encode('ascii') for offset in offsets[1:]))
    document.extend(
        f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
        f'startxref\n{xref_offset}\n%%EOF\n'.encode('ascii')
    )
    return bytes(document)


def _pdf_lines(strategy: str, report_date: date, rows: list[dict[str, str]]) -> list[str]:
    lines = [f'ATHENA {strategy.replace("_", " ")} SIGNAL REPORT', f'Date: {report_date.isoformat()}', f'Signals: {len(rows)}', '']
    if not rows:
        lines.append('No setups or signals were recorded for this strategy on this date.')
        return lines
    for index, row in enumerate(rows, start=1):
        lines.extend([
            f'{index}. {row.get("symbol") or "Unknown symbol"} / {row.get("signal") or "No direction"} / {row.get("decision_state") or "UNKNOWN"}',
            f'Time: {row.get("timestamp") or "Unknown"}',
            f'Execution: {row.get("executed") or "NO"} / {row.get("execution_status") or "NOT_EXECUTED"}',
            f'Score: {row.get("score") or "N/A"}',
            f'Reason: {row.get("reason") or "No reason recorded."}',
            '',
        ])
    return lines


@login_required
@require_GET
def strategy_report_view(request, strategy_slug: str):
    try:
        report_date = _requested_date(request)
        strategy, rows = _report_rows(request, strategy_slug, report_date)
    except ValueError as error:
        return JsonResponse({'detail': str(error)}, status=400)
    return JsonResponse({'strategy': strategy, 'date': report_date.isoformat(), 'rows': rows})


@login_required
@require_GET
def strategy_report_pdf_view(request, strategy_slug: str):
    try:
        report_date = _requested_date(request)
        strategy, rows = _report_rows(request, strategy_slug, report_date)
    except ValueError as error:
        return JsonResponse({'detail': str(error)}, status=400)
    response = HttpResponse(
        _build_pdf(_pdf_lines(strategy, report_date, rows)),
        content_type='application/pdf',
    )
    filename = f'{strategy.lower()}_{report_date.isoformat()}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
