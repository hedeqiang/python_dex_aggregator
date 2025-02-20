# DEX Aggregator Client

一个用于与去中心化交易所聚合器交互的 Python 客户端，支持多链交易和代币兑换。

## 功能特点

- 支持多条区块链网络 (Ethereum, BSC, Polygon, Arbitrum, Optimism, Avalanche)
- 集成 OKX DEX 聚合器 API
- 支持代币询价和兑换
- 自动处理代币授权
- 完整的日志记录
- Web3 工具集成
- 异常处理机制

## 环境要求

- Python 3.8+
- pip

### 使用方法
#### 基本用法

##### 安装
```bash
pip install dex-aggregator
```

##### 初始化服务
```php
from dex_aggregator import QuoteService, SwapService

quote_service = QuoteService()
swap_service = SwapService()
```

##### 获取询价
```php
quote = quote_service.get_quote(
    chain_id="1",  # Ethereum
    from_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH
    to_token="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",    # USDC
    amount="0.0001"
)
```

##### 执行兑换
```php
tx_hash = swap_service.execute_swap(
    chain_id="1",  # Ethereum
    from_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH
    to_token="0xdac17f958d2ee523a2206206994597c13d831ec7",  # USDT
    amount="0.0001",
    recipient_address="0x76bE3c7A8966D44240411b057B12d2fa72131ad6",
    slippage="0.03",
)
```

##### 获取支持的链
```php
chains = quote_service.okx_client.get_supported_chains(56)
print("Supported chains:", chains)
```

##### 获取币种列表
```php
tokens = quote_service.okx_client.get_token_list("56")
print("Tokens:", tokens)
```

## 支持的网络

- Ethereum (Chain ID: 1)
- BNB Chain (Chain ID: 56)
- Polygon (Chain ID: 137)
- Arbitrum (Chain ID: 42161)
- Optimism (Chain ID: 10)
- Avalanche (Chain ID: 43114)

## 错误处理

该项目实现了完整的错误处理机制，主要包括以下异常类：

- `DexAggregatorException`: 基础异常类
- `ProviderError`: Provider 相关错误
- `QuoteError`: 询价相关错误
- `SwapError`: 兑换相关错误
- `ConfigError`: 配置相关错误

## 日志记录

项目使用 Python 的 logging 模块进行日志记录。可以通过环境变量 `LOG_LEVEL` 设置日志级别。

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

[MIT License](LICENSE)

## 安全提示

- 请勿在代码中直接硬编码私钥和 API 密钥
- 确保 `.env` 文件不会被提交到版本控制系统
- 在生产环境中使用安全的密钥管理系统
- 定期更新依赖包以修复潜在的安全漏洞

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

