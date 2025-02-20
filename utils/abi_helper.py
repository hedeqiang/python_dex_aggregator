import json
import os
from typing import Dict
from core.exceptions import ConfigError
from utils.logger import get_logger

logger = get_logger(__name__)

class ABIHelper:
    _instance = None
    _abis: Dict[str, list] = {}
    
    def __init__(self):
        self._load_abis()
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_abis(self):
        """加载所有ABI文件"""
        # 修改为从core/abis目录加载
        current_dir = os.path.dirname(os.path.dirname(__file__))
        abi_dir = os.path.join(current_dir, 'core', 'abis')
        
        if not os.path.exists(abi_dir):
            logger.error(f"ABI directory not found: {abi_dir}")
            raise ConfigError(f"ABI directory not found: {abi_dir}")
            
        for filename in os.listdir(abi_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(abi_dir, filename)
                contract_name = filename[:-5]  # 移除.json后缀
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self._abis[contract_name] = json.load(f)
                        logger.debug(f"Loaded ABI for {contract_name} from {file_path}")
                except Exception as e:
                    logger.error(f"Failed to load ABI file {file_path}: {str(e)}")
                    raise ConfigError(f"Failed to load ABI file {file_path}: {str(e)}")
    
    def get_abi(self, contract_name: str) -> list:
        """获取指定合约的ABI"""
        if contract_name not in self._abis:
            raise ConfigError(f"ABI not found for contract: {contract_name}")
        return self._abis[contract_name] 