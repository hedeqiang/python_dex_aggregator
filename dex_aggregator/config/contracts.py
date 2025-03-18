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
        "quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
    },
    "10": {  # Optimism
        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "router": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
        "quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
    },
    "43114": {  # Avalanche
        "factory": "0x740b1c1de25031C31FF4fC9A62f554A55cdC1baD",
        "router": "0xbb00FF08d01D300023C629E8fFfFcb65A5a578cE",
        "quoter": "0xbe0F5544EC67e9B3b2D979aaA43f18Fd87E6257F"
    },
    "480": { # WorldChain
        "factory": "0x7a5028BDa40e7B173C278C5342087826455ea25a",
        "router": "0x091AD9e2e6e5eD44c1c66dB50e49A601F9f36cF6",
        "quoter": "0x10158D43e6cc414deE1Bd1eB0EfC6a5cBCfF244c"
    },
    "324": {  # zkSync
        "factory": "0x8FdA5a7a8dCA67BBcDd10F02Fa0649A937215422",
        "router": "0x99c56385daBCE3E81d8499d0b8d0257aBC07E8A3",
        "quoter": "0x8Cb537fc92E26d8EBBb760E632c95484b6Ea3e28"
    },
    "7777777": { # Zora
        "factory": "0x7145F8aeef1f6510E92164038E1B6F8cB2c42Cbb",
        "router": "0x7De04c96BE5159c3b5CeffC82aa176dc81281557",
        "quoter": "0x11867e1b3348F3ce4FcC170BC5af3d23E07E64Df"
    },
    "42220": { # Celo
        "factory": "0xAfE208a311B21f13EF87E33A90049fC17A7acDEc",
        "router": "0x5615CDAb10dc425a742d643d949a7F474C01abc4",
        "quoter": "0x82825d0554fA07f7FC52Ab63c961F330fdEFa8E8"
    },
    "81457": { # Blast
        "factory": "0x792edAdE80af5fC680d96a2eD80A44247D2Cf6Fd",
        "router": "0x549FEB8c9bd4c12Ad2AB27022dA12492aC452B66",
        "quoter": "0x6Cdcd65e03c1CEc3730AeeCd45bc140D57A25C77"
    },
    "8453": { # Base
        "factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
        "router": "0x2626664c2603336E57B271c5C0b26F421741e481",
        "quoter": "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"
    },
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