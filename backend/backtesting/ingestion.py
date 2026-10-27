from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db import transaction

from .models import HistoricalCandle, HistoricalDataset


def _number(row, *names, default=0.0):
    for name in names:
        value = row.get(name)
        if value not in (None, ''):
            return float(value)
    return default


def _timestamp(value, source_timezone):
    raw = str(value).strip()
    try:
        parsed = datetime.fromtimestamp(float(raw), tz=dt_timezone.utc)
    except ValueError:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo(source_timezone))
    return int(parsed.astimezone(dt_timezone.utc).timestamp())


def _csv_rows(upload, source_timezone):
    text = upload.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError('CSV must include a header row.')
    normalized = [{str(key).strip().lower(): value for key, value in row.items()} for row in reader]
    return normalized, reader.fieldnames


def _parquet_rows(upload):
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise ValueError('Parquet import requires the optional pyarrow package.') from error
    table = parquet.read_table(io.BytesIO(upload.read()))
    rows = table.to_pylist()
    return [{str(key).strip().lower(): value for key, value in row.items()} for row in rows], list(table.column_names)


@transaction.atomic
def import_dataset(*, user, account, upload, source_timezone, timeframe, symbol, version, source='IMPORT'):
    if timeframe not in {'M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'}:
        raise ValueError('Unsupported dataset timeframe.')
    if source_timezone not in {'UTC'}:
        try:
            ZoneInfo(source_timezone)
        except Exception as error:
            raise ValueError(f'Unknown dataset timezone: {source_timezone}') from error
    extension = upload.name.lower().rsplit('.', 1)[-1] if '.' in upload.name else ''
    if extension == 'csv':
        rows, columns = _csv_rows(upload, source_timezone)
    elif extension in {'parquet', 'pq'}:
        rows, columns = _parquet_rows(upload)
    else:
        raise ValueError('Upload must be a CSV or Parquet file.')
    if not rows:
        raise ValueError('Dataset contains no rows.')
    timestamp_key = next((key for key in ('time', 'timestamp', 'datetime', 'date') if key in rows[0]), None)
    if not timestamp_key or not {'open', 'high', 'low', 'close'} <= set(rows[0]):
        raise ValueError('Dataset must contain time/timestamp/date and open, high, low, close columns.')
    candles = []
    for row in rows:
        timestamp = _timestamp(row[timestamp_key], source_timezone)
        candles.append({'time': timestamp, 'open': _number(row, 'open'), 'high': _number(row, 'high'),
                        'low': _number(row, 'low'), 'close': _number(row, 'close'),
                        'volume': int(_number(row, 'volume', 'tick_volume', default=0))})
    candles.sort(key=lambda candle: candle['time'])
    dataset = HistoricalDataset.objects.create(user_id=user.pk, account_id=account.pk, source=source, symbol=symbol,
        timezone=source_timezone, timeframe=timeframe, start_time=candles[0]['time'], end_time=candles[-1]['time'],
        version=version or '1', row_count=len(candles), metadata={'filename': upload.name, 'columns': columns})
    HistoricalCandle.objects.bulk_create([
        HistoricalCandle(user_id=user.pk, account_id=account.pk, symbol=symbol, timeframe=timeframe, dataset=dataset,
                         timestamp=candle['time'], open=candle['open'], high=candle['high'], low=candle['low'],
                         close=candle['close'], volume=candle['volume']) for candle in candles
    ], batch_size=1000)
    return dataset
