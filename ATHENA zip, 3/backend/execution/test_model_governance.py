import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from .model_training import model_status


class ModelGovernanceTests(SimpleTestCase):
    def test_model_status_exposes_governance_metadata(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            model_path = root / 'model.json'
            metadata_path = root / 'model_metadata.json'
            model_path.write_text('model', encoding='utf-8')
            metadata_path.write_text(json.dumps({
                'version': 'xgb-20260826120000',
                'trainedAt': '2026-08-26T12:00:00+00:00',
                'featureSchema': ['feature_a'],
                'trainingPeriod': {'from': 1, 'to': 2},
                'checksum': 'abc',
                'validation': {'accuracy': 0.75},
            }), encoding='utf-8')
            with patch('backend.execution.model_training._paths', return_value=(root, model_path, metadata_path)):
                status = model_status()

        self.assertTrue(status['trained'])
        self.assertEqual(status['version'], 'xgb-20260826120000')
        self.assertEqual(status['featureSchema'], ['feature_a'])
        self.assertEqual(status['trainingPeriod']['to'], 2)
        self.assertEqual(status['checksum'], 'abc')
        self.assertEqual(status['validation']['accuracy'], 0.75)
