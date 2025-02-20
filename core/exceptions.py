class DexAggregatorException(Exception):
    """基础异常类"""
    def __init__(self, message: str, code: int = None):
        self.message = message
        self.code = code
        super().__init__(self.message)

class ProviderError(DexAggregatorException):
    """Provider相关错误"""
    pass

class QuoteError(DexAggregatorException):
    """询价相关错误"""
    pass

class SwapError(DexAggregatorException):
    """兑换相关错误"""
    pass

class ConfigError(DexAggregatorException):
    """配置相关错误"""
    pass
 