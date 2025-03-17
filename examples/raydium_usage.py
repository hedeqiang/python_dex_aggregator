from dex_aggregator.core.factory import DexFactory
from dex_aggregator.providers.raydium.constants import WSOL_MINT

# 创建 Raydium Provider 实例
dex = DexFactory.create_provider("raydium")

# 获取报价 (SOL -> USDC)
# SOL 会自动转换为 wSOL
quote = dex.get_quote(
    chain_id="501",  # Solana
    from_token="11111111111111111111111111111111",  # SOL (会自动转换为 wSOL)
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.001",
    slippage="0.5"  # 0.5% 滑点
)

print("Quote details:")
print(quote)

# # 也可以直接使用 wSOL
# quote_wsol = dex.get_quote(
#     chain_id="501",  # Solana
#     from_token=WSOL_MINT,  # wSOL
#     to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
#     amount="0.001",
#     slippage="0.5"  # 0.5% 滑点
# )
#
# print("\nQuote details (using wSOL):")
# print(quote_wsol)

# 执行兑换 (自动处理 SOL 的 wrap/unwrap)
# 注意：
# 1. 如果输入/输出是 SOL，会自动处理 wrap/unwrap
# 2. 如果没有提供代币账户，会自动创建
# 3. 如果提供了代币账户，会使用指定的账户
tx_hash = dex.swap(
    chain_id="501",
    from_token="11111111111111111111111111111111",  # SOL
    to_token="Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    amount="0.0001",
    recipient_address="ATEhXjPVGaBUFVMyvCWETS5R9ZPAh7ke6SX2tdsMqC5f",
    slippage="0.5"  # 0.5% 滑点
)

print("\nTransaction hash:")
print(tx_hash)