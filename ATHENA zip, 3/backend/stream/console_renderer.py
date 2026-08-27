from __future__ import annotations

from .formatters import format_event, format_market_header, format_orchestrated_analysis


class ConsoleStreamRenderer:
    def __init__(self, *, write=None):
        self.write = write or print

    def render_market(self, *, symbol: str, bid: float, ask: float, spread: float) -> None:
        self.write(format_market_header(symbol=symbol, bid=bid, ask=ask, spread=spread))

    def render_event(self, event) -> None:
        self.write(format_event(event))

    def render_orchestrated_analysis(self, payload: dict) -> None:
        """
        Render orchestrated execution analysis in unified format.
        
        Produces the human-readable output as specified in the architecture document.
        """
        output = format_orchestrated_analysis(payload)
        self.write(output)
