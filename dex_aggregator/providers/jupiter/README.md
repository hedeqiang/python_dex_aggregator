# Jupiter Provider

Jupiter 是 Solana 生态系统中最强大的 DEX 聚合器，支持多种交易路由和优化。本提供者实现了与 Jupiter Swap API v1 的集成，实现了 Solana 上的代币交换功能。

## 功能特点

- **智能路由**: 基于 Jupiter 的高效路由引擎，找到跨多个 DEX 的最佳交易路径
- **多 AMM 支持**: 支持 Solana 上的多个 AMM，包括 Meteora、Orca、Raydium 等
- **SOL 原生支持**: 自动处理 SOL 的 wrap/unwrap 操作
- **指定接收地址**: 支持将交易结果直接发送到指定的接收地址
- **滑点保护**: 可自定义滑点参数，防止价格波动过大造成损失
- **中间代币限制**: 支持限制中间代币，确保路由通过高流动性的代币对

## 使用示例

### 查询兑换报价

```python
from dex_aggregator.core.factory import DexFactory

# 创建 Jupiter provider 实例
jupiter = DexFactory.create_provider("jupiter")

# 获取报价 (SOL -> USDC)
quote = jupiter.get_quote(
    chain_id="501",  # Solana
    from_token="11111111111111111111111111111111",  # SOL
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.01",
    slippage="0.5"  # 0.5% 滑点
)

print(f"输入: {quote['fromAmount']} SOL")
print(f"输出: {quote['humanAmount']} USDC")
print(f"价格影响: {quote['priceImpact']}%")
```

### 执行兑换交易

```python
# 执行兑换
tx_hash = jupiter.swap(
    chain_id="501",
    from_token="11111111111111111111111111111111",  # SOL
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.01",
    slippage="0.5"  # 0.5% 滑点
)

print(f"交易哈希: {tx_hash}")
```

### 发送到其他地址

```python
# 执行兑换并发送到其他地址
tx_hash = jupiter.swap(
    chain_id="501",
    from_token="11111111111111111111111111111111",  # SOL
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.01",
    recipient_address="ATEhXjPVGaBUFVMyvCWETS5R9ZPAh7ke6SX2tdsMqC5f",  # 接收人地址
    slippage="0.5"  # 0.5% 滑点
)
```

## 参数说明

### get_quote 方法参数

| 参数名 | 说明 | 类型 | 是否必需 | 默认值 |
|--------|------|------|----------|--------|
| chain_id | 链ID (Solana 为 "501") | str | 是 | - |
| from_token | 源代币地址 | str | 是 | - |
| to_token | 目标代币地址 | str | 是 | - |
| amount | 输入数量 | str | 是 | - |
| slippage | 滑点百分比 | str | 否 | "0.5" |
| restrictIntermediateTokens | 是否限制中间代币 (注意: 布尔值会自动转换为小写字符串"true"/"false") | bool | 否 | True |

### swap 方法参数

| 参数名 | 说明 | 类型 | 是否必需 | 默认值 |
|--------|------|------|----------|--------|
| chain_id | 链ID (Solana 为 "501") | str | 是 | - |
| from_token | 源代币地址 | str | 是 | - |
| to_token | 目标代币地址 | str | 是 | - |
| amount | 输入数量 | str | 是 | - |
| recipient_address | 接收人地址 | str | 否 | None |
| slippage | 滑点百分比 | str | 否 | "0.5" |

## 相关链接

- [Jupiter 官方文档](https://docs.jup.ag/)
- [Jupiter Swap API 文档](https://dev.jup.ag/docs/api/swap-api/quote)
- [Jupiter Terminal](https://terminal.jup.ag/) 