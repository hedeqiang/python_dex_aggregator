from dex_aggregator.core.factory import DexFactory
from dex_aggregator.providers.jupiter.constants import WSOL_MINT

# 创建 Jupiter Provider 实例
dex = DexFactory.create_provider("jupiter")

# 示例一：获取报价 (SOL -> USDC)
# SOL 会自动转换为 wSOL
print("获取报价 (SOL -> USDC)...")
quote = dex.get_quote(
    chain_id="501",  # Solana
    from_token="11111111111111111111111111111111",  # SOL (会自动转换为 wSOL)
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.00001",  # 使用极小额测试
    slippage="0.5"  # 0.5% 滑点
)

print("Quote details:")
print(f"输入: {quote['fromAmount']} SOL")
print(f"输出: {quote['humanAmount']} USDC")
print(f"价格影响: {quote['priceImpact']}%")
print(f"估计 Gas: {quote['estimatedGas']}")

# 示例二：也可以直接使用 wSOL
print("\n获取报价 (wSOL -> USDC)...")
quote_wsol = dex.get_quote(
    chain_id="501",  # Solana
    from_token=WSOL_MINT,  # wSOL
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.00001",  # 使用极小额测试
    slippage="0.5"  # 0.5% 滑点
)

print("\nQuote details (using wSOL):")
print(f"输入: {quote_wsol['fromAmount']} wSOL")
print(f"输出: {quote_wsol['humanAmount']} USDC")

# 示例三：限制中间代币
print("\n获取报价 (SOL -> USDC，限制中间代币)...")
quote_restricted = dex.get_quote(
    chain_id="501",
    from_token="11111111111111111111111111111111",  # SOL
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.00001",  # 使用极小额测试
    slippage="0.5",
    restrictIntermediateTokens=True  # 限制使用高流动性的中间代币
)

print("\nQuote details (with restricted intermediate tokens):")
print(f"输入: {quote_restricted['fromAmount']} SOL")
print(f"输出: {quote_restricted['humanAmount']} USDC")

# 示例四：执行兑换 (自动处理 SOL 的 wrap/unwrap)
# 注释掉以避免实际执行交易
"""
print("\n执行兑换 (SOL -> USDC)...")
tx_hash = dex.swap(
    chain_id="501",
    from_token="11111111111111111111111111111111",  # SOL
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.00001",
    slippage="0.5"  # 0.5% 滑点
)

print("Transaction hash:")
print(tx_hash)
"""

# 示例五：执行兑换并指定接收人地址（代币将直接发送到指定地址）
# 取消注释以执行交易，请确保钱包中有足够的 SOL
# print("\n执行兑换并发送到指定地址 (SOL -> USDC)...")
# tx_hash = dex.swap(
#     chain_id="501",
#     from_token="11111111111111111111111111111111",  # SOL
#     to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
#     amount="0.00001",
#     recipient_address="ATEhXjPVGaBUFVMyvCWETS5R9ZPAh7ke6SX2tdsMqC5f",  # 接收人地址
#     slippage="0.5"  # 0.5% 滑点
# )
#
# print("Transaction hash (with recipient):")
# print(tx_hash)

# 示例六：使用 USDC 交换 USDT
# 注释掉以避免实际执行交易

# print("\n执行兑换 (USDC -> USDT)...")
# tx_hash = dex.swap(
#     chain_id="501",
#     from_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
#     to_token="Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
#     amount="0.01",  # 使用小额测试
#     slippage="0.5",  # 0.5% 滑点
#     recipient_address="ATEhXjPVGaBUFVMyvCWETS5R9ZPAh7ke6SX2tdsMqC5f",  # 接收人地址
# )
#
# print("Transaction hash (USDC to USDT):")
# print(tx_hash)
