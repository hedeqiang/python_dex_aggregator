# DEX Aggregator Client

一个用于与去中心化交易所聚合器交互的 Python 客户端,支持多链交易和代币兑换。

> 暂时不建议在生产环境中使用（会有破坏性更新操作）,仅供学习和研究使用。

[![PyPI version](https://badge.fury.io/py/dex-aggregator.svg)](https://badge.fury.io/py/dex-aggregator)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/downloads/)
[![GitHub issues](https://img.shields.io/github/issues/hedeqiang/python_dex_aggregator)](https://github.com/hedeqiang/python_dex_aggregator/issues)

## 特性

- 多链支持 (Ethereum, BSC, Polygon, Arbitrum, Optimism, Avalanche, Solana)
- 工厂模式设计,易于扩展
- 完整的错误处理和日志记录
- Web3 工具集成
- 自动处理代币授权
- 支持多个 DEX 聚合器(当前支持 OKX(EVM,Solana)、Uniswap V3、PancakeSwap)

## 安装

```bash
pip install dex-aggregator
```

## 快速开始

### 基础用法

```python
from dex_aggregator.core.factory import DexFactory

# 创建 DEX Provider 实例
dex = DexFactory.create_provider("okx")

# 获取报价
quote = dex.get_quote(
    chain_id="1",  # Ethereum
    from_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH
    to_token="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC
    amount="0.1"
)

# 执行兑换
tx_hash = dex.swap(
    chain_id="1",
    from_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH
    to_token="0xdac17f958d2ee523a2206206994597c13d831ec7",  # USDT
    amount="0.1",
    recipient_address="0x76bE3c7A8966D44240411b057B12d2fa72131ad6",
    slippage="0.03"
)
```

### 查询支持的链和代币

```python
# 获取支持的链
chains = dex.client.get_supported_chains()

# 获取指定链上支持的代币列表
tokens = dex.client.get_token_list("1")  # Ethereum
```

## 支持的网络

| 网络 | Chain ID |
|------|----------|
| Ethereum | 1 |
| BNB Chain | 56 |
| Polygon | 137 |
| Arbitrum | 42161 |
| Optimism | 10 |
| Avalanche | 43114 |

## 配置

### 环境变量

创建 `.env` 文件并配置以下变量:

```bash
# API Keys
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase

# RPC Endpoints
ETH_RPC_URL=https://eth-mainnet.example.com
BSC_RPC_URL=https://bsc-mainnet.example.com
POLYGON_RPC_URL=https://polygon-mainnet.example.com
ARBITRUM_RPC_URL=https://arbitrum-mainnet.example.com
OPTIMISM_RPC_URL=https://optimism-mainnet.example.com
AVALANCHE_RPC_URL=https://avalanche-mainnet.example.com

# Wallet Config
WALLET_PRIVATE_KEY=your_wallet_private_key
WALLET_ADDRESS=your_wallet_address

# Log Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Solana Config
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_WALLET_ADDRESS=your_solana_wallet_address
SOLANA_WALLET_PRIVATE_KEY=your_solana_wallet_private_key
```

### Web3 Provider 配置

默认支持的 RPC 节点可在 settings.py 中配置:

```python
WEB3_CONFIG = {
    "providers": {
        "1": "https://eth-mainnet.g.alchemy.com/v2/your-api-key",
        "56": "https://bsc-dataseed.binance.org",
        # ...
    }
}
```

## 错误处理

该项目实现了完整的错误处理机制:

```python
try:
    quote = dex.get_quote(...)
except DexAggregatorException as e:
    logger.error(f"DEX aggregator error: {e}")
except ProviderError as e:
    logger.error(f"Provider error: {e}")
except QuoteError as e:
    logger.error(f"Quote error: {e}")
```

## 开发指南

### 添加新的 DEX Provider

1. 实现 IDexProvider 接口:

```python
from dex_aggregator.core.interfaces import IDexProvider

class NewDexProvider(IDexProvider):
    def get_quote(self, chain_id: str, from_token: str, 
                  to_token: str, amount: str, **kwargs) -> Dict:
        # 实现获取报价逻辑
        pass
        
    def swap(self, chain_id: str, from_token: str,
             to_token: str, amount: str, **kwargs) -> str:
        # 实现兑换逻辑
        pass
        
    def check_and_approve(self, chain_id: str, token_address: str, 
                         owner_address: str, amount: int) -> Optional[str]:
        # 实现授权检查逻辑
        pass
```

2. 在工厂类中注册:

```python
class DexFactory:
    _providers = {
        "okx": OKXProvider,
        "new_dex": NewDexProvider
    }
```

## 日志记录

项目使用 Python 的 logging 模块进行日志记录:

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 获取logger实例
logger = logging.getLogger(__name__)
```

## 安全建议

- 不要在代码中硬编码私钥和 API 密钥
- 确保 `.env` 文件不被提交到版本控制系统
- 在生产环境中使用安全的密钥管理系统
- 定期更新依赖包以修复潜在的安全漏洞
- 使用 Web3 签名时注意检查交易参数

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

[MIT License](LICENSE)

## 联系方式

如有问题或建议,请提交 [Issue](https://github.com/hedeqiang/python_dex_aggregator/issues) 或 [Pull Request](https://github.com/hedeqiang/python_dex_aggregator/pulls)。

