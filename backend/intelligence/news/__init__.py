from .contracts import InstrumentNewsState, NewsEvent, NewsIntelligence

__all__ = ['InstrumentNewsState', 'NewsEngine', 'NewsEvent', 'NewsIntelligence']


def __getattr__(name):
    if name == 'NewsEngine':
        from .engine import NewsEngine

        return NewsEngine
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
