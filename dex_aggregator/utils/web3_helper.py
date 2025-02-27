from web3 import Web3, HTTPProvider
from typing import Dict, Optional, Union, List
from dex_aggregator.config.settings import WEB3_CONFIG
from dex_aggregator.core.exceptions import ConfigError
from web3.exceptions import ContractLogicError
from dex_aggregator.utils.abi_helper import ABIHelper
from dex_aggregator.utils.logger import get_logger
from decimal import Decimal
from web3.middleware import ExtraDataToPOAMiddleware

logger = get_logger(__name__)


class Web3Helper:
    _instances: Dict[str, 'Web3Helper'] = {}
    
    def __init__(self, chain_id: str):
        if chain_id not in WEB3_CONFIG["providers"]:
            raise ConfigError(f"Chain ID {chain_id} not supported")
        
        self.chain_id = chain_id
        self.web3 = Web3(HTTPProvider(WEB3_CONFIG["providers"][chain_id]))
        
        # 为 BSC 等 POA 链添加中间件
        if chain_id in ["56", "97"]:  # BSC 主网和测试网
            self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        self.abi_helper = ABIHelper.get_instance()

    @classmethod
    def get_instance(cls, chain_id: str) -> 'Web3Helper':
        if chain_id not in cls._instances:
            cls._instances[chain_id] = cls(chain_id)
        return cls._instances[chain_id]

    def get_allowance(self, token_address: str, owner_address: str, spender_address: str) -> int:
        """查询代币授权额度"""
        contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(token_address),
            abi=self.abi_helper.get_abi('erc20')
        )
        return contract.functions.allowance(
            self.web3.to_checksum_address(owner_address),
            self.web3.to_checksum_address(spender_address)
        ).call()

    def send_transaction(self, transaction: Dict, private_key: str) -> str:
        """发送交易"""
        signed_txn = self.web3.eth.account.sign_transaction(
            transaction,
            private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(
            signed_txn.raw_transaction
        )
        return self.web3.to_hex(tx_hash)

    def get_token_info(self, token_address: str) -> Dict:
        """
        获取代币基本信息
        
        Args:
            token_address: 代币合约地址
            
        Returns:
            Dict: {
                'name': str,
                'symbol': str,
                'decimals': int,
                'total_supply': int
            }
        """
        try:
            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_address),
                abi=self.abi_helper.get_abi('erc20')
            )
            
            return {
                'name': contract.functions.name().call(),
                'symbol': contract.functions.symbol().call(),
                'decimals': contract.functions.decimals().call(),
                'total_supply': contract.functions.totalSupply().call()
            }
        except ContractLogicError as e:
            logger.error(f"Failed to get token info for {token_address}: {str(e)}")
            raise

    def get_token_decimals(self, token_address: str) -> int:
        """获取代币精度
        Args:
            token_address: 代币合约地址
        Returns:
            int: 代币精度
        """
        try:
            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_address),
                abi=self.abi_helper.get_abi('erc20')
            )
            return contract.functions.decimals().call()
        except ContractLogicError as e:
            logger.error(f"Failed to get decimals for token {token_address}: {str(e)}")
            raise


    def get_token_balance(self, token_address: str, wallet_address: str, abi: list) -> int:
        """
        获取代币余额
        
        Args:
            token_address: 代币合约地址
            wallet_address: 钱包地址
            abi: 代币合约ABI
            
        Returns:
            int: 代币余额(原始值，未经精度转换)
        """
        try:
            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_address),
                abi=abi
            )
            return contract.functions.balanceOf(
                self.web3.to_checksum_address(wallet_address)
            ).call()
        except ContractLogicError as e:
            logger.error(f"Failed to get balance for token {token_address}, wallet {wallet_address}: {str(e)}")
            raise

    def format_token_amount(self, amount: int, decimals: int) -> str:
        """
        格式化代币金额（从原始值转换为带精度的字符串）
        
        Args:
            amount: 原始金额
            decimals: 代币精度
            
        Returns:
            str: 格式化后的金额
        """
        return str(amount / (10 ** decimals))

    def parse_token_amount(self, amount: str, decimals: int) -> int:
        """
        将带小数点的金额转换为链上精度
        
        Args:
            amount: 带小数点的金额字符串
            decimals: 代币精度
            
        Returns:
            int: 转换后的金额
        """
        try:
            # 移除字符串中的所有空格
            amount = amount.strip()
            # 将字符串转换为浮点数
            float_amount = float(amount)
            # 转换为链上精度
            raw_amount = int(float_amount * (10 ** decimals))
            return raw_amount
        except ValueError as e:
            logger.error(f"Failed to parse amount {amount}: {str(e)}")
            raise ValueError(f"Invalid amount format: {amount}")

    def is_contract(self, address: str) -> bool:
        """
        检查地址是否为合约地址
        
        Args:
            address: 以太坊地址
            
        Returns:
            bool: 是否为合约地址
        """
        code = self.web3.eth.get_code(self.web3.to_checksum_address(address))
        return code != b''

    def get_native_balance(self, address: str) -> int:
        """
        获取原生代币余额（如ETH、BNB等）
        
        Args:
            address: 钱包地址
            
        Returns:
            int: 原生代币余额(单位: Wei)
        """
        return self.web3.eth.get_balance(self.web3.to_checksum_address(address))

    def get_transaction(self, tx_hash: str) -> Dict:
        """
        获取交易详情
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            Dict: 交易详情
        """
        try:
            tx = self.web3.eth.get_transaction(tx_hash)
            return dict(tx)
        except Exception as e:
            logger.error(f"Failed to get transaction {tx_hash}: {str(e)}")
            raise

    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """
        获取交易收据
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            Optional[Dict]: 交易收据，如果交易未确认则返回None
        """
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            return dict(receipt) if receipt else None
        except Exception as e:
            logger.error(f"Failed to get transaction receipt {tx_hash}: {str(e)}")
            raise

    def wait_for_transaction(self, tx_hash: str, timeout: int = 180, poll_interval: float = 0.1) -> Dict:
        """
        等待交易确认
        
        Args:
            tx_hash: 交易哈希
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）
            
        Returns:
            Dict: 交易收据
        """
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=timeout, poll_latency=poll_interval
            )
            return dict(receipt)
        except Exception as e:
            logger.error(f"Failed to wait for transaction {tx_hash}: {str(e)}")
            raise

    def estimate_gas(self, transaction: Dict) -> int:
        """
        估算交易gas用量
        
        Args:
            transaction: 交易参数
            
        Returns:
            int: 预估的gas用量
        """
        try:
            return self.web3.eth.estimate_gas(transaction)
        except Exception as e:
            logger.error(f"Failed to estimate gas: {str(e)}")
            raise

    def get_block(self, block_identifier: Union[str, int]) -> Dict:
        """
        获取区块信息
        
        Args:
            block_identifier: 区块号或区块哈希
            
        Returns:
            Dict: 区块信息
        """
        try:
            block = self.web3.eth.get_block(block_identifier)
            return dict(block)
        except Exception as e:
            logger.error(f"Failed to get block {block_identifier}: {str(e)}")
            raise

    def get_logs(self, from_block: int, to_block: int, address: Optional[str] = None, 
                 topics: Optional[List] = None) -> List[Dict]:
        """
        获取事件日志
        
        Args:
            from_block: 起始区块
            to_block: 结束区块
            address: 合约地址（可选）
            topics: 主题过滤器（可选）
            
        Returns:
            List[Dict]: 事件日志列表
        """
        try:
            filter_params = {
                'fromBlock': from_block,
                'toBlock': to_block
            }
            if address:
                filter_params['address'] = self.web3.to_checksum_address(address)
            if topics:
                filter_params['topics'] = topics

            logs = self.web3.eth.get_logs(filter_params)
            return [dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get logs: {str(e)}")
            raise

    def get_transaction_count(self, address: str, block_identifier: str = 'latest') -> int:
        """
        获取账户的nonce值
        
        Args:
            address: 账户地址
            block_identifier: 区块标识符
            
        Returns:
            int: nonce值
        """
        try:
            return self.web3.eth.get_transaction_count(
                self.web3.to_checksum_address(address),
                block_identifier
            )
        except Exception as e:
            logger.error(f"Failed to get transaction count for {address}: {str(e)}")
            raise

    def get_gas_price(self) -> int:
        """
        获取当前gas价格
        
        Returns:
            int: gas价格（wei）
        """
        try:
            return self.web3.eth.gas_price
        except Exception as e:
            logger.error(f"Failed to get gas price: {str(e)}")
            raise

    def format_amount(self, amount: Union[int, str], decimals: int) -> str:
        """
        格式化代币金额（从wei转换为带小数点的字符串）
        
        Args:
            amount: 原始金额（wei）
            decimals: 代币精度
            
        Returns:
            str: 格式化后的金额
        """
        try:
            amount_decimal = Decimal(str(amount)) / Decimal(str(10 ** decimals))
            return f"{amount_decimal:.{decimals}f}".rstrip('0').rstrip('.')
        except Exception as e:
            logger.error(f"Failed to format amount {amount}: {str(e)}")
            raise

    def is_valid_address(self, address: str) -> bool:
        """
        检查地址是否有效
        
        Args:
            address: 以太坊地址
            
        Returns:
            bool: 是否为有效地址
        """
        try:
            return self.web3.is_address(address)
        except Exception as e:
            logger.error(f"Failed to validate address {address}: {str(e)}")
            return False 