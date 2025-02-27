import os
from typing import Dict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API配置
API_CONFIG = {
    "OKX": {
        "base_url": "https://www.okx.com/api/v5/dex/aggregator",
        "api_key": os.getenv("OKX_API_KEY"),
        "secret_key": os.getenv("OKX_SECRET_KEY"),
        "passphrase": os.getenv("OKX_PASSPHRASE"),
    }
}

# Web3配置
WEB3_CONFIG = {
    "providers": {
        "1": os.getenv("ETH_RPC_URL"),
        "56": os.getenv("BSC_RPC_URL"),
        "137": os.getenv("POLYGON_RPC_URL"),
        "42161": os.getenv("ARBITRUM_RPC_URL"),
        "10": os.getenv("OPTIMISM_RPC_URL"),
        "43114": os.getenv("AVALANCHE_RPC_URL"),
        "501": os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    }
}

# 钱包配置
WALLET_CONFIG = {
    "default": {
        "address": os.getenv("DEFAULT_WALLET_ADDRESS"),
        "private_key": os.getenv("DEFAULT_WALLET_PRIVATE_KEY")
    },
    "solana": {
        "address": os.getenv("SOLANA_WALLET_ADDRESS"),
        "private_key": os.getenv("SOLANA_WALLET_PRIVATE_KEY")
    }
}

# 如果设置了其他钱包的环境变量，添加到配置中
if os.getenv("WALLET2_ADDRESS") and os.getenv("WALLET2_PRIVATE_KEY"):
    WALLET_CONFIG["wallet2"] = {
        "address": os.getenv("WALLET2_ADDRESS"),
        "private_key": os.getenv("WALLET2_PRIVATE_KEY")
    }

# 原生代币配置
NATIVE_TOKENS = {
    "1": {
        "symbol": "ETH",
        "decimals": 18,
        "name": "Ethereum"
    },
    "56": {
        "symbol": "BNB",
        "decimals": 18,
        "name": "BNB Chain"
    },
    "137": {
        "symbol": "MATIC",
        "decimals": 18,
        "name": "Polygon"
    },
    "42161": {
        "symbol": "ETH",
        "decimals": 18,
        "name": "Arbitrum"
    },
    "10": {
        "symbol": "ETH",
        "decimals": 18,
        "name": "Optimism"
    },
    "43114": {
        "symbol": "AVAX",
        "decimals": 18,
        "name": "Avalanche"
    },
    "501": {  # Solana
        "symbol": "SOL",
        "decimals": 9,
        "name": "Solana"
    }
}

# 日志配置
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "formatter": "standard",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "propagate": True
        },
    }
} 