from __future__ import annotations


class ProviderRegistry:
    def __init__(self):
        self._providers = {}

    def register(self, provider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str):
        return self._providers.get(name)

    def health(self) -> dict[str, bool]:
        return {name: provider is not None for name, provider in self._providers.items()}
