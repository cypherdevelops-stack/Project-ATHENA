from __future__ import annotations

from pathlib import Path
import os

_active_engine: 'XGBoostEngine | None' = None

FEATURE_NAMES = (
    'htf_bullish',
    'ltf_bullish',
    'in_poi',
    'liquidity_swept',
    'displacement',
    'mss',
    'session_aligned',
    'spread_ok',
    'volatility_normal',
    'correlation_allowed',
    'poi_strength',
    'rule_score',
)


class XGBoostEngineError(RuntimeError):
    pass


def build_feature_vector(*, candidate: dict, context: dict) -> list[float]:
    direction = candidate.get('direction')
    bullish = direction == 'BUY'
    setup = candidate.get('setup') or {}
    components = candidate.get('scoreComponents') or {}
    return [
        float((candidate.get('regimeContext') == 'BULLISH') == bullish),
        float((context.get('m1_structure') == 'BULLISH') == bullish),
        float(candidate.get('entryZone') is not None and candidate.get('currentPrice') is not None and candidate['entryZone']['lower'] <= candidate['currentPrice'] <= candidate['entryZone']['upper']),
        float(setup.get('missing', []).count('LIQUIDITY_SWEEP') == 0),
        float(setup.get('missing', []).count('DISPLACEMENT') == 0),
        float(setup.get('missing', []).count('MSS') == 0),
        float(context.get('session_aligned', True)),
        float(context.get('spread_ok', True)),
        float(context.get('volatility', 'NORMAL') == 'NORMAL'),
        float(context.get('correlation_allowed', True)),
        float(candidate.get('strength', 0) or 0),
        float(candidate.get('score', components.get('ruleScore', 0)) or 0) / 100,
    ]


class XGBoostEngine:
    """Optional probability model; it can inform ranking but never authorizes a trade."""

    def __init__(self, model=None):
        self.model = model
        self.trained = model is not None

    def train(self, samples: list[dict], labels: list[int]) -> dict:
        if not samples or len(samples) != len(labels):
            raise XGBoostEngineError('Training samples and labels must be non-empty and have equal length.')
        try:
            from xgboost import XGBClassifier
        except ImportError as error:
            raise XGBoostEngineError('XGBoost is not installed.') from error
        if len(set(labels)) < 2:
            raise XGBoostEngineError('Training requires both positive and negative labels.')
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective='binary:logistic',
            eval_metric='logloss',
            random_state=42,
        )
        self.model.fit(samples, labels)
        self.trained = True
        return {'status': 'TRAINED', 'samples': len(samples), 'features': list(FEATURE_NAMES)}

    def predict(self, *, candidate: dict, context: dict) -> dict:
        if not self.trained or self.model is None:
            return {'status': 'UNKNOWN', 'probability': None, 'reason': 'No trained XGBoost model is loaded.'}
        probability = float(self.model.predict_proba([build_feature_vector(candidate=candidate, context=context)])[0][1])
        return {'status': 'PASS' if probability >= 0.5 else 'BLOCK', 'probability': round(probability, 4), 'features': list(FEATURE_NAMES)}

    def save(self, path: str | Path) -> None:
        if not self.trained or self.model is None:
            raise XGBoostEngineError('Cannot save an untrained model.')
        self.model.save_model(str(path))

    @classmethod
    def load(cls, path: str | Path) -> 'XGBoostEngine':
        try:
            from xgboost import XGBClassifier
        except ImportError as error:
            raise XGBoostEngineError('XGBoost is not installed.') from error
        model = XGBClassifier()
        model.load_model(str(path))
        return cls(model=model)


def configured_xgboost_engine() -> XGBoostEngine | None:
    """Load the configured model artifact, if one exists; missing artifacts stay disabled."""
    path = os.environ.get('ATHENA_XGBOOST_MODEL') or str(Path(__file__).resolve().parents[2] / 'data' / 'models' / 'xgboost_scalping.json')
    if not path or not Path(path).is_file():
        return None
    return XGBoostEngine.load(path)


def get_active_xgboost_engine() -> XGBoostEngine | None:
    global _active_engine
    if _active_engine is not None:
        return _active_engine
    _active_engine = configured_xgboost_engine()
    return _active_engine


def set_active_xgboost_engine(engine: XGBoostEngine) -> None:
    global _active_engine
    _active_engine = engine
