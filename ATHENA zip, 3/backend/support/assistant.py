from dataclasses import dataclass

from .nlp import analyze


@dataclass(frozen=True)
class AssistantAnswer:
    text: str
    intent: str
    grounded: bool = True


def answer_help_request(message: str) -> AssistantAnswer:
    """Safe, dependency-free ATHENA assistant used until a provider is configured."""
    nlp = analyze(message)

    if nlp.unsafe:
        return AssistantAnswer(
            'I can explain ATHENA workflows and safety controls, but I cannot place orders, change risk policy, bypass a guardian lock, or reveal credentials. Use the Executioner and Settings screens for authorized actions.',
            'safety_refusal',
        )

    intent = nlp.intent
    responses = {
        'orchestration': 'The Orchestration screen combines market regime, scalping and day-trading engine states, portfolio risk availability, the current decision, and recent alerts. An approved decision still requires the configured execution policy and confirmation.',
        'execution': 'Use Executioner to inspect analysis and execution state. Paper and demo actions are isolated from live trading; live actions remain subject to account permissions, fresh-decision checks, slippage limits, and ATHENA guardian controls.',
        'backtesting': 'Backtesting lets you inspect historical market data, import supported CSV or Parquet datasets, replay candles, and review outcomes. It is isolated from live execution.',
        'accounts': 'Add and verify broker accounts from Settings. The MT5 handshake checks connectivity, permissions, market discovery, and broker constraints before an account can be used by ATHENA.',
        'journal': 'Journal sessions are used to record market observations and events. Keep the notes tied to the asset, market session, regime, and decision evidence so they remain useful for review.',
        'navigation': 'Use the left sidebar to open Dashboard, Executioner, Orchestration, Backtesting, Journal, or Settings. The Help button stays available at the bottom-right on authenticated screens.',
        'general': 'I can help with ATHENA navigation, accounts and MT5 connectivity, orchestration decisions, execution modes, backtesting, journaling, and safety controls. Tell me what you are trying to do and include the screen or error you see.',
    }
    return AssistantAnswer(responses[intent], intent)
