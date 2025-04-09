"""
Jupiter DEX 聚合器高级用法示例
===============================

本示例展示了使用 Jupiter DEX 聚合器进行交易的高级用法。
Jupiter 是 Solana 上功能最强大的 DEX 聚合器，支持多种代币交换路径。

官方文档: https://dev.jup.ag/docs/api/swap-api/quote
"""

from dex_aggregator.core.factory import DexFactory
from dex_aggregator.providers.jupiter.constants import WSOL_MINT, SOL_ADDRESS
import json

# 常用代币地址
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOL = SOL_ADDRESS
WSOL = WSOL_MINT
BONK = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
BSOL = "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj"

# 创建 Jupiter Provider 实例
jupiter = DexFactory.create_provider("jupiter")

def get_token_name(token_address):
    """获取代币名称的简单工具函数"""
    token_map = {
        SOL: "SOL",
        WSOL: "wSOL",
        USDC: "USDC",
        USDT: "USDT",
        BONK: "BONK",
        BSOL: "bSOL"
    }
    return token_map.get(token_address, token_address[:8] + "...")

def print_quote_details(quote, title="Quote Details"):
    """格式化打印报价详情"""
    from_token = get_token_name(quote["fromTokenAddress"])
    to_token = get_token_name(quote["toTokenAddress"])
    
    print(f"\n{title}")
    print("=" * len(title))
    print(f"交易对: {from_token} -> {to_token}")
    print(f"输入数量: {quote['fromAmount']} {from_token}")
    print(f"输出数量: {quote['humanAmount']} {to_token}")
    print(f"原始输出数量: {quote['toAmount']}")
    print(f"价格影响: {quote['priceImpact']}%")
    print(f"估计 Gas: {quote['estimatedGas']}")
    
    # 打印路由计划（如果有）
    if "quoteResponse" in quote and "routePlan" in quote["quoteResponse"]:
        route_plan = quote["quoteResponse"]["routePlan"]
        print("\n路由计划:")
        for i, route in enumerate(route_plan):
            if "swapInfo" in route:
                swap_info = route["swapInfo"]
                amm_name = swap_info.get("label", "Unknown AMM")
                percentage = route.get("percent", 100)
                from_token_route = get_token_name(swap_info.get("inputMint", ""))
                to_token_route = get_token_name(swap_info.get("outputMint", ""))
                print(f"  路径 {i+1}: {percentage}% 通过 {amm_name} ({from_token_route} -> {to_token_route})")

# 示例 1: 基本报价查询
def example_basic_quote():
    """基本报价查询示例"""
    quote = jupiter.get_quote(
        chain_id="501",
        from_token=SOL,
        to_token=USDC,
        amount="0.01"
    )
    print_quote_details(quote, "基本报价查询 (SOL -> USDC)")

# 示例 2: 自定义滑点
def example_custom_slippage():
    """自定义滑点示例"""
    quote = jupiter.get_quote(
        chain_id="501",
        from_token=USDC,
        to_token=SOL,
        amount="1",
        slippage="1.0"  # 1% 滑点，默认是 0.5%
    )
    print_quote_details(quote, "自定义滑点示例 (USDC -> SOL, 1% 滑点)")

# 示例 3: 限制中间代币
def example_restrict_intermediate_tokens():
    """限制中间代币示例"""
    # 注意：在内部实现中，布尔值 True/False 会被转换为字符串 "true"/"false"
    # 这是因为 Jupiter API 期望接收小写字符串形式的布尔值
    
    # 不限制中间代币
    quote_unrestricted = jupiter.get_quote(
        chain_id="501",
        from_token=SOL,
        to_token=BONK,
        amount="0.1",
        restrictIntermediateTokens=False
    )
    print_quote_details(quote_unrestricted, "不限制中间代币 (SOL -> BONK)")
    
    # 限制中间代币
    quote_restricted = jupiter.get_quote(
        chain_id="501",
        from_token=SOL,
        to_token=BONK,
        amount="0.1",
        restrictIntermediateTokens=True
    )
    print_quote_details(quote_restricted, "限制中间代币 (SOL -> BONK)")

# 示例 4: 发送到其他地址
def example_swap_to_recipient():
    """发送到其他地址示例（仅展示代码，不实际执行）"""
    print("\n发送到其他地址示例")
    print("=" * 30)
    print("以下代码展示如何将交易结果发送到其他地址:")
    print("""
tx_hash = jupiter.swap(
    chain_id="501",
    from_token=SOL,
    to_token=USDC,
    amount="0.01",
    recipient_address="ATEhXjPVGaBUFVMyvCWETS5R9ZPAh7ke6SX2tdsMqC5f",  # 接收人地址
    slippage="0.5"
)
    """)
    print("实际执行时，交易结果会直接发送到指定的接收人地址，而不是交易发起人的地址。")

# 执行示例
if __name__ == "__main__":
    print("Jupiter DEX 聚合器高级用法示例")
    print("===============================")
    
    # 运行各个示例
    example_basic_quote()
    example_custom_slippage()
    example_restrict_intermediate_tokens()
    example_swap_to_recipient()
    
    print("\n所有示例执行完毕") 