from dex_aggregator.core.factory import DexFactory

# 创建 Solana Provider 实例
dex = DexFactory.create_provider("okx_solana")

# 获取报价
quote = dex.get_quote(
    chain_id="501",  # Solana
    from_token="11111111111111111111111111111111",  # SOL
    to_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount="0.001"
)

print("Quote details:")
print(quote)
#
# # 执行兑换
tx_hash = dex.swap(
    chain_id="501",
    from_token="11111111111111111111111111111111",  # SOL
    to_token="Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    amount="0.0001",
    recipient_address="ATEhXjPVGaBUFVMyvCWETS5R9ZPAh7ke6SX2tdsMqC5f",
)
