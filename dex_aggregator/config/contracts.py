"""合约地址配置"""

UNISWAP_V3_CONTRACTS = {
    "1": {  # Ethereum Mainnet
        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
    },
    "56": {  # Binance Smart Chain
        "factory": "0xdB1d10011AD0Ff90774D0C6Bb92e5C5c8b4461F7",
        "router": "0xB971eF87ede563556b2ED4b1C0b0019111Dd85d2",
        "quoter": "0x78D78E420Da98ad378D7799bE8f4AF69033EB077"
    },
    "137": {  # Polygon
        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "router": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
        "quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
    },
    "42161": {  # Arbitrum
        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "router": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
        "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6"
    },
    "10": {  # Optimism
        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "router": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
        "quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
    }
} 