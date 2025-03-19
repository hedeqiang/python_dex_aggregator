from dex_aggregator.core.factory import DexFactory

import json

# 创建 Uniswap Provider 实例
dex = DexFactory.create_provider("uniswap")

WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
#
# 获取 WETH/USDT 报价
quote = dex.get_quote(
    chain_id="1",
    from_token=WETH,  # WETH
    to_token=USDT,    # USDT
    amount="0.0001"   # 0.0001 WETH
)

print(json.dumps(quote, indent=4))

# # 执行兑换
# tx_hash = dex.swap(
#     chain_id="1",
#     from_token=WETH,  # WETH
#     to_token=USDT,    # USDT
#     amount="0.0001",
#     recipient="0x76bE3c7A8966D44240411b057B12d2fa72131ad6",
#     slippage="0.003"  # 0.3% 滑点
# )
#
# print(f"Swap transaction hash: {tx_hash}")

# WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
# USDT = "0x55d398326f99059ff775485246999027b3197955"
#
# quote = dex.get_quote(
#     chain_id="56",
#     from_token=WBNB,  # WBNB
#     to_token=USDT,    # USDT
#     amount="0.0001"   # 0.0001 WBNB
# )
# print(json.dumps(quote, indent=4))

#
# tx_hash = dex.swap(
#     chain_id="56",
#     from_token=WBNB,  # WBNB
#     to_token=USDT,    # USDT
#     amount="0.001",
#     recipient="0x76bE3c7A8966D44240411b057B12d2fa72131ad6",
#     slippage="0.003"  # 0.3% 滑点
# )
#
# print(f"Swap transaction hash: {tx_hash}")