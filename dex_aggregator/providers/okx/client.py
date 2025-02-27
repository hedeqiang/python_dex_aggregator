import hmac
import base64
import requests
from typing import Dict, Optional
from urllib.parse import urlencode
from datetime import datetime, timezone

from dex_aggregator.core.exceptions import ProviderError
from dex_aggregator.config.settings import API_CONFIG
from dex_aggregator.utils.logger import get_logger

logger = get_logger(__name__)

class OKXClient:
    def __init__(self):
        self.config = API_CONFIG["OKX"]
        self.base_url = "https://www.okx.com"
        self.api_key = self.config["api_key"]
        self.secret_key = self.config["secret_key"]
        self.passphrase = self.config["passphrase"]

    def _get_timestamp(self) -> str:
        """获取ISO格式的UTC时间戳"""
        dt = datetime.now(timezone.utc)
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def _generate_signature(self, timestamp: str, method: str, request_path: str) -> str:
        """
        生成签名
        timestamp + method + requestPath + body
        
        注意：对于 GET 请求，body 为空，但 requestPath 需要包含查询参数
        """
        message = f"{timestamp}{method}{request_path}"
        logger.debug(f"Pre-hash String: {message}")
        
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        logger.debug(f"Generated Signature: {signature}")
        return signature

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """发送请求"""
        try:
            # 1. 构建完整的 API 路径
            api_path = '/api/v5/dex/aggregator'
            full_endpoint = f"{api_path}{endpoint}"
            
            # 2. 处理查询参数
            query_string = ""
            if params:
                # 确保参数值为字符串类型
                params = {k: str(v) for k, v in params.items() if v is not None}
                # 按键排序参数
                sorted_params = sorted(params.items())
                query_string = "?" + urlencode(sorted_params)
            
            # 3. 构建用于签名的请求路径
            request_path = f"{full_endpoint}{query_string}"
            
            # 4. 生成时间戳和签名
            timestamp = self._get_timestamp()
            signature = self._generate_signature(timestamp, method, request_path)

            # 5. 准备请求头
            headers = {
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-SIGN": signature,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": self.passphrase,
                "Content-Type": "application/json"
            }

            # 6. 构建完整的 URL
            url = f"{self.base_url}{request_path}"
            
            # 调试信息
            logger.debug(f"Timestamp: {timestamp}")
            logger.debug(f"Method: {method}")
            logger.debug(f"Request Path for Signature: {request_path}")
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request Headers: {headers}")
            logger.debug(f"Request Params: {params}")

            # 7. 发送请求 - 注意这里不再使用 params 参数，因为已经包含在 URL 中
            response = requests.request(
                method=method,
                url=url,
                headers=headers
            )
            
            logger.debug(f"Response Status: {response.status_code}")
            logger.debug(f"Response Text: {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise ProviderError(f"OKX API request failed: {str(e)}")

    def get_supported_chains(self, chain_id: Optional[str] = None) -> Dict:
        """获取支持的链列表"""
        params = {"chainId": chain_id} if chain_id else None
        return self._request("GET", "/supported/chain", params)

    def get_token_list(self, chain_id: str) -> Dict:
        """获取币种列表"""
        params = {"chainId": chain_id}
        return self._request("GET", "/all-tokens", params)

    def get_liquidity(self,chain_id: str) -> Dict:
        """获取流动性"""
        params = {"chainId": chain_id}
        return self._request("GET", "/liquidity", params)

    def get_quote(self, params: Dict) -> Dict:
        """获取询价信息"""
        return self._request("GET", "/quote", params)

    def get_swap(self, params: Dict) -> Dict:
        """获取兑换信息"""
        return self._request("GET", "/swap", params)

    def get_approve_transaction(self, params: Dict) -> Dict:
        """获取授权交易信息"""
        return self._request("GET", "/approve-transaction", params)

    def get_history(self, chain_id: str, tx_hash: str) -> Dict:
        """根据 txhash 查询单链兑换最终交易状态。"""
        params = {"chainId": chain_id, "txHash": tx_hash}
        return self._request("GET", "/history", params)

    def get_swap_instruction(self, params: Dict) -> Dict:
        """获取兑换指令"""
        return self._request("GET", "/swap-instruction", params)