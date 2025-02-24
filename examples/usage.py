from dex_aggregator.core.factory import DexFactory

# 创建 provider 实例
dex = DexFactory.create_provider("okx")

# 获取报价
quote = dex.get_quote(
    chain_id="56",
    from_token="0x55d398326f99059ff775485246999027b3197955",
    to_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
    amount="1"
)

print(quote)

print(dex.client.get_supported_chains())



# # # 执行兑换
# tx_hash = dex.swap(
#     chain_id="56",  # Binance Smart Chain
#     from_token="0x55d398326f99059ff775485246999027b3197955",  # USDT
#     to_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # BNB
#     amount="1",
#     recipient_address="0x76bE3c7A8966D44240411b057B12d2fa72131ad6",
#     slippage="0.03",
#     wallet_name="default"  # 可选，默认使用default钱包
# )
# print(f"Swap transaction hash: {tx_hash}")


