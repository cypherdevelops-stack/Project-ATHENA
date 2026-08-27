from __future__ import annotations

import json
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from django.conf import settings

from backend.accounts.models import Account
from backend.market.service import market_data_service

from .training_data import build_training_dataset
from .model_validation import validate_samples
from .xgboost_engine import FEATURE_NAMES, XGBoostEngine, set_active_xgboost_engine

_executor = ThreadPoolExecutor(max_workers=1)
_lock = Lock()
_jobs: dict[str, dict] = {}
_active_job_id: str | None = None
DEFAULT_TRAINING_CANDLES = 2000


def training_candle_count() -> int:
    try:
        configured = int(os.environ.get('ATHENA_TRAINING_CANDLES', DEFAULT_TRAINING_CANDLES))
    except ValueError:
        configured = DEFAULT_TRAINING_CANDLES
    return max(200, min(configured, 10000))


def _paths() -> tuple[Path, Path, Path]:
    training_dir = settings.BASE_DIR / 'assets' / 'training'
    return training_dir, settings.BASE_DIR / 'data' / 'models' / 'xgboost_scalping.json', training_dir / 'model_metadata.json'


def model_status() -> dict:
    _, model_path, metadata_path = _paths()
    if not model_path.is_file():
        return {'trained': False, 'trainedAt': None, 'model': None}
    metadata = {}
    if metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            pass
    return {'trained': True, 'trainedAt': metadata.get('trainedAt'), 'samples': metadata.get('samples'), 'positiveLabels': metadata.get('positiveLabels'), 'candleCount': metadata.get('candleCount'), 'model': 'xgboost_scalping', 'version': metadata.get('version'), 'featureSchema': metadata.get('featureSchema'), 'trainingPeriod': metadata.get('trainingPeriod'), 'checksum': metadata.get('checksum'), 'validation': metadata.get('validation')}


def validate_saved_model() -> dict:
    training_dir, _, _ = _paths()
    dataset_path = training_dir / 'xgboost_scalping_dataset.json'
    if not dataset_path.is_file():
        raise ValueError('No saved training dataset is available.')
    payload = json.loads(dataset_path.read_text(encoding='utf-8'))
    result = validate_samples(samples=payload['features'], labels=payload['labels'])
    metadata_path = _paths()[2]
    metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.is_file() else {}
    metadata['validation'] = result
    metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
    return result


def _update(job_id: str, **values) -> None:
    with _lock:
        _jobs[job_id].update(values)


def _run_training(job_id: str, account_id: int) -> None:
    try:
        _update(job_id, phase='COLLECTING_DATA', progress=15, message='Collecting M1 and M5 candle history from MT5.')
        account = Account.objects.get(pk=account_id, enabled=True)
        candle_count = training_candle_count()
        data = market_data_service.fetch(account, timeframes=('M1', 'M5'), candle_count=candle_count)
        _update(job_id, phase='BUILDING_DATASET', progress=35, message='Building point-in-time features and forward outcome labels.')
        samples, labels = build_training_dataset(m1_candles=data.candles['M1'], m5_candles=data.candles['M5'])
        training_dir, model_path, metadata_path = _paths()
        training_dir.mkdir(parents=True, exist_ok=True)
        (training_dir / 'xgboost_scalping_dataset.json').write_text(json.dumps({'features': samples, 'labels': labels}), encoding='utf-8')
        _update(job_id, phase='TRAINING', progress=55, message=f'Training candidate XGBoost on {len(samples)} labeled setups.')
        engine = XGBoostEngine()
        result = engine.train(samples, labels)
        _update(job_id, phase='VALIDATING', progress=75, message='Validating the candidate on unseen chronological samples.')
        validation = validate_saved_candidate(samples=samples, labels=labels, engine=engine)
        metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.is_file() else {}
        previous_validation = metadata.get('validation') or {}
        previous_score = float(previous_validation.get('winRate', previous_validation.get('accuracy', -1)))
        candidate_score = float(validation.get('winRate', validation.get('accuracy', 0)))
        model_path.parent.mkdir(parents=True, exist_ok=True)
        trained_at = datetime.now(timezone.utc).isoformat()
        version = f"xgb-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        promoted = not model_path.is_file() or candidate_score > previous_score
        if promoted:
            if model_path.is_file():
                model_path.replace(model_path.with_name('xgboost_scalping.previous.json'))
            candidate_path = model_path.with_name('xgboost_scalping.candidate.json')
            engine.save(candidate_path)
            candidate_path.replace(model_path)
            checksum = hashlib.sha256(model_path.read_bytes()).hexdigest()
            metadata = {
                'version': version,
                'trainedAt': trained_at,
                'trainingPeriod': {'from': data.candles['M1'][0]['time'], 'to': data.candles['M1'][-1]['time']},
                'samples': len(samples), 'positiveLabels': sum(labels), 'candleCount': candle_count,
                'featureSchema': list(FEATURE_NAMES), 'validation': validation, 'checksum': checksum,
                'previousModel': 'xgboost_scalping.previous.json' if model_path.with_name('xgboost_scalping.previous.json').is_file() else None,
            }
            metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
            set_active_xgboost_engine(engine)
            final_status = 'PROMOTED'
            message = 'Candidate validated, promoted, and connected to execution.'
        else:
            final_status = 'REJECTED'
            message = 'Candidate validation did not improve the active model; active model was preserved.'
        _update(job_id, phase='COMPLETE', progress=100, message=message, result={**result, 'status': final_status, 'trainedAt': trained_at, 'positiveLabels': sum(labels), 'candleCount': candle_count, 'validation': validation, 'version': version})
    except Exception as error:
        _update(job_id, phase='ERROR', progress=100, message='Training stopped safely.', error=str(error))
    finally:
        global _active_job_id
        with _lock:
            _active_job_id = None


def start_training(account_id: int) -> dict:
    global _active_job_id
    with _lock:
        if _active_job_id and _jobs.get(_active_job_id, {}).get('phase') not in {'COMPLETE', 'ERROR'}:
            return _jobs[_active_job_id].copy()
        job_id = uuid4().hex
        _jobs[job_id] = {'jobId': job_id, 'phase': 'STARTING', 'progress': 5, 'message': 'Preparing model training.', 'result': None, 'error': None}
        _active_job_id = job_id
    _executor.submit(_run_training, job_id, account_id)
    return _jobs[job_id].copy()


def validate_saved_candidate(*, samples: list[list[float]], labels: list[int], engine: XGBoostEngine) -> dict:
    from .model_validation import validate_samples
    return validate_samples(samples=samples, labels=labels, engine=engine)


def training_status(job_id: str | None = None) -> dict:
    with _lock:
        selected = job_id or _active_job_id
        if selected and selected in _jobs:
            return _jobs[selected].copy()
    return {'jobId': None, 'phase': 'IDLE', 'progress': 0, 'message': 'No model training is running.', 'result': None, 'error': None}
