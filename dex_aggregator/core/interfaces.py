from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, Optional

class IDexProvider(ABC):
    """DEX 提供者接口"""
    
    @abstractmethod
    def client(self):
        """获取底层客户端实例"""
        pass
    
    @abstractmethod
    def get_quote(self, chain_id: str, from_token: str, 
                  to_token: str, amount: str, **kwargs) -> Dict:
        """获取报价"""
        pass
    
    @abstractmethod
    def swap(self, chain_id: str, from_token: str,to_token: str, amount: str, recipient_address: Optional[str] = None,  slippage: str = "0.03", **kwargs) -> str:
        """执行兑换"""
        pass
    
    @abstractmethod
    def check_and_approve(self, chain_id: str, token_address: str, 
                         owner_address: str, amount: int) -> Optional[str]:
        """检查并处理代币授权"""
        pass