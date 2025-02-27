import json
import os
from typing import Dict
from dex_aggregator.core.exceptions import ConfigError
from dex_aggregator.utils.logger import get_logger

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
        current_dir = os.path.dirname(os.path.dirname(__file__))
        abi_dir = os.path.join(current_dir, 'core', 'abis')
        
        if not os.path.exists(abi_dir):
            logger.error(f"ABI directory not found: {abi_dir}")
            raise ConfigError(f"ABI directory not found: {abi_dir}")
            
        for root, dirs, files in os.walk(abi_dir):
            for filename in files:
                if filename.endswith('.json'):
                    file_path = os.path.join(root, filename)
                    # 获取相对于abi_dir的路径
                    relative_path = os.path.relpath(file_path, abi_dir)
                    # 移除.json后缀
                    contract_name = os.path.splitext(relative_path)[0]
                    # 将路径分隔符替换为/
                    contract_name = contract_name.replace(os.path.sep, '/')
                    
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