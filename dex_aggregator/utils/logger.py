import logging
import logging.config
from typing import Optional
from dex_aggregator.config.settings import LOGGING_CONFIG

# 配置日志
logging.config.dictConfig(LOGGING_CONFIG)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取logger实例
    
    Args:
        name: 日志名称，通常使用 __name__
        
    Returns:
        logging.Logger: 配置好的logger实例
    """
    return logging.getLogger(name)

class LoggerMixin:
    """
    Logger Mixin类，可以被其他类继承以获得日志功能
    
    Example:
        class MyClass(LoggerMixin):
            def __init__(self):
                self.logger = self.get_logger()
    """
    
    @property
    def logger(self) -> logging.Logger:
        """
        获取当前类的logger
        
        Returns:
            logging.Logger: 当前类的logger实例
        """
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger

def log_error(logger: logging.Logger):
    """
    错误日志装饰器
    
    Args:
        logger: Logger实例
        
    Example:
        @log_error(logger)
        def my_function():
            # 函数代码
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator 