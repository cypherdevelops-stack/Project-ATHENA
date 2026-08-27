from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Literal
from uuid import UUID, uuid4


DecisionAction = Literal[
    'SCALP_LONG_APPROVED',
    'SCALP_SHORT_APPROVED',
    'DAY_BUY_DEVELOPING',
    'DAY_SELL_DEVELOPING',
    'OBSERVE',
    'BLOCKED',
    'ERROR',
]
StrategyName = Literal['SCALPING', 'DAY_TRADING']
Direction = Literal['BUY', 'SELL']


class ContractValidationError(ValueError):
    pass


def _finite_number(value: float, field_name: str) -> float:
    value = float(value)
    if not isfinite(value):
        raise ContractValidationError(f'{field_name} must be finite.')
    return value


def _aware_timestamp(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ContractValidationError(f'{field_name} must be timezone-aware.')
    return value


@dataclass(frozen=True)
class CanonicalTradeSetup:
    strategy: StrategyName
    direction: Direction
    symbol: str
    entry: float
    stop_loss: float
    take_profit1: float
    take_profit2: float
    volume: float
    state: str = 'RISK_APPROVED'
    score: float = 0.0
    risk_reward: float | None = None
    expires_at: datetime | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.strategy not in {'SCALPING', 'DAY_TRADING'}:
            raise ContractValidationError('setup.strategy is invalid.')
        if self.direction not in {'BUY', 'SELL'}:
            raise ContractValidationError('setup.direction is invalid.')
        if not self.symbol:
            raise ContractValidationError('setup.symbol is required.')
        for name in ('entry', 'stop_loss', 'take_profit1', 'take_profit2', 'volume'):
            if _finite_number(getattr(self, name), f'setup.{name}') <= 0:
                raise ContractValidationError(f'setup.{name} must be greater than zero.')
        if self.volume <= 0:
            raise ContractValidationError('setup.volume must be greater than zero.')
        if self.score < 0 or self.score > 100:
            raise ContractValidationError('setup.score must be between 0 and 100.')
        if self.risk_reward is not None and _finite_number(self.risk_reward, 'setup.risk_reward') <= 0:
            raise ContractValidationError('setup.risk_reward must be greater than zero.')
        if self.expires_at is not None:
            _aware_timestamp(self.expires_at, 'setup.expires_at')

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.update({
            'stopLoss': payload.pop('stop_loss'),
            'takeProfit1': payload.pop('take_profit1'),
            'takeProfit2': payload.pop('take_profit2'),
            'riskReward': payload.pop('risk_reward'),
            'expiresAt': payload.pop('expires_at').isoformat() if self.expires_at else None,
        })
        return payload


@dataclass(frozen=True)
class OrchestrationDecision:
    action: DecisionAction
    reason: str
    strategy: StrategyName | None = None
    direction: Direction | None = None
    reason_codes: list[str] = field(default_factory=list)
    decision_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    setup: CanonicalTradeSetup | None = None

    def __post_init__(self) -> None:
        valid_actions = {
            'SCALP_LONG_APPROVED', 'SCALP_SHORT_APPROVED',
            'DAY_BUY_DEVELOPING', 'DAY_SELL_DEVELOPING',
            'OBSERVE', 'BLOCKED', 'ERROR',
        }
        if self.action not in valid_actions:
            raise ContractValidationError('decision.action is invalid.')
        if not self.reason:
            raise ContractValidationError('decision.reason is required.')
        if self.strategy is not None and self.strategy not in {'SCALPING', 'DAY_TRADING'}:
            raise ContractValidationError('decision.strategy is invalid.')
        if self.direction is not None and self.direction not in {'BUY', 'SELL'}:
            raise ContractValidationError('decision.direction is invalid.')
        _aware_timestamp(self.created_at, 'decision.created_at')
        if self.expires_at is not None:
            _aware_timestamp(self.expires_at, 'decision.expires_at')

    @classmethod
    def from_analysis(cls, analysis: dict[str, Any]) -> 'OrchestrationDecision':
        orchestration = analysis.get('orchestration') or {}
        decision = orchestration.get('decision') or {}
        action = decision.get('action', orchestration.get('status', 'OBSERVE'))
        return cls(
            action=action,
            reason=decision.get('reason', orchestration.get('reason', 'No decision reason supplied.')),
            strategy=decision.get('strategy'),
            direction=decision.get('direction'),
            reason_codes=list(decision.get('reasonCodes') or []),
        )

    def as_payload(self) -> dict[str, Any]:
        return {
            'decisionId': str(self.decision_id),
            'action': self.action,
            'status': self.action,
            'strategy': self.strategy,
            'direction': self.direction,
            'reasonCodes': self.reason_codes,
            'reason': self.reason,
            'snapshotTimestamp': self.created_at.isoformat(),
            'expiresAt': self.expires_at.isoformat() if self.expires_at else None,
            'setup': self.setup.as_payload() if self.setup else None,
        }


@dataclass(frozen=True)
class ExecutionAttempt:
    decision_id: UUID
    idempotency_key: str
    account_id: int
    symbol: str
    status: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    broker_response: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.idempotency_key:
            raise ContractValidationError('execution.idempotency_key is required.')
        if not self.symbol:
            raise ContractValidationError('execution.symbol is required.')
        _aware_timestamp(self.created_at, 'execution.created_at')
        if self.completed_at is not None:
            _aware_timestamp(self.completed_at, 'execution.completed_at')


@dataclass(frozen=True)
class BrokerPositionSnapshot:
    account_id: int
    symbol: str
    ticket: int
    direction: Direction
    volume: float
    price_open: float
    stop_loss: float | None = None
    take_profit: float | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.symbol or self.ticket <= 0:
            raise ContractValidationError('broker position symbol and ticket are required.')
        if self.direction not in {'BUY', 'SELL'}:
            raise ContractValidationError('broker position direction is invalid.')
        if _finite_number(self.volume, 'broker position volume') <= 0:
            raise ContractValidationError('broker position volume must be greater than zero.')
        if _finite_number(self.price_open, 'broker position price_open') <= 0:
            raise ContractValidationError('broker position price_open must be greater than zero.')
        _aware_timestamp(self.observed_at, 'broker position observed_at')
