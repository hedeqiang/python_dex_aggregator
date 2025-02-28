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

PANCAKESWAP_V3_CONTRACTS = {
    "1": {  # Ethereum
        "factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
        "router": "0x13f4EA83D0bd40E75C8222255bc855a974568Dd4",
        "quoter": "0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997"
    },
    "56": {  # BSC
        "factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
        "router": "0x13f4EA83D0bd40E75C8222255bc855a974568Dd4",
        "quoter": "0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997"
    },
    "1101": {  # zkEVM
        "factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
        "router": "0x678Aa4bF4E210cf2166753e054d5b7c31cc7fa86",
        "quoter": "0x4c650FB471fe4e0f476fD3437C3411B1122c4e3B"
    },
    "42161": {  # Arbitrum
        "factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
        "router": "0x32226588378236Fd0c7c4053999F88aC0e5cAc77",
        "quoter": "0x3652Fc6EDcbD76161b8554388867d3dAb65eCA93"
    },
    "59144": {  # Linea
        "factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
        "router": "0x678Aa4bF4E210cf2166753e054d5b7c31cc7fa86",
        "quoter": "0x4c650FB471fe4e0f476fD3437C3411B1122c4e3B"
    },
    "8453": {  # Base
        "factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
        "router": "0x678Aa4bF4E210cf2166753e054d5b7c31cc7fa86",
        "quoter": "0x4c650FB471fe4e0f476fD3437C3411B1122c4e3B"
    },
    "204": {  # opBNB
        "factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
        "router": "0x678Aa4bF4E210cf2166753e054d5b7c31cc7fa86",
        "quoter": "0x4c650FB471fe4e0f476fD3437C3411B1122c4e3B"
    },
    "324": {  # zkSync
        "factory": "0x1BB72E0CbbEA93c08f535fc7856E0338D7F7a8aB",
        "router": "0xf8b59f3c3Ab33200ec80a8A58b2aA5F5D2a8944C",
        "quoter": "0x3d146FcE6c1006857750cBe8aF44f76a28041CCc"
    }
} 