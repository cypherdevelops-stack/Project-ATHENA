from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from backend.execution.training_data import build_training_dataset
from backend.execution.xgboost_engine import XGBoostEngine, XGBoostEngineError


class Command(BaseCommand):
    help = 'Build a point-in-time candle dataset, label forward outcomes, and train XGBoost.'

    def add_arguments(self, parser):
        parser.add_argument('input', type=Path, help='JSON file containing m1 candles or {"m1": [...], "m5": [...]}')
        parser.add_argument('--output', type=Path, default=Path('data/xgboost_scalping.json'))
        parser.add_argument('--horizon', type=int, default=12)

    def handle(self, *args, **options):
        input_path = options['input']
        try:
            payload = json.loads(input_path.read_text(encoding='utf-8'))
            m1 = payload.get('m1', payload) if isinstance(payload, dict) else payload
            m5 = payload.get('m5') if isinstance(payload, dict) else None
            samples, labels = build_training_dataset(m1_candles=m1, m5_candles=m5, horizon=options['horizon'])
            engine = XGBoostEngine()
            result = engine.train(samples, labels)
            output_path = options['output']
            output_path.parent.mkdir(parents=True, exist_ok=True)
            engine.save(output_path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise CommandError(f'Unable to build training data: {error}') from error
        except XGBoostEngineError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"{result['status']}: {result['samples']} samples -> {output_path}"))
