from typing import Dict, Type
from .interfaces import IDexProvider
from ..providers.okx.provider import OKXProvider

class DexFactory:
    """DEX 工厂类"""
    
    _providers: Dict[str, Type[IDexProvider]] = {
        "okx": OKXProvider
    }
    
    @classmethod
    def create_provider(cls, provider_name: str) -> IDexProvider:
        """创建 DEX 提供者实例"""
        if provider_name not in cls._providers:
            raise ValueError(f"Unsupported provider: {provider_name}")
        return cls._providers[provider_name]() 