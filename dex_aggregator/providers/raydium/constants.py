"""Raydium API 配置"""

# Wrapped SOL address
WSOL_MINT = "So11111111111111111111111111111111111111112"

API_URLS = {
    "BASE_HOST": "https://api-v3.raydium.io",
    "OWNER_BASE_HOST": "https://owner-v1.raydium.io",
    "SERVICE_BASE_HOST": "https://service.raydium.io",
    "MONITOR_BASE_HOST": "https://monitor.raydium.io",
    "SERVICE_1_BASE_HOST": "https://service-v1.raydium.io",
    "SWAP_HOST": "https://transaction-v1.raydium.io",

    # API endpoints
    "SEND_TRANSACTION": "/send-transaction",
    "FARM_ARP": "/main/farm/info",
    "FARM_ARP_LINE": "/main/farm-apr-tv",
    "CLMM_CONFIG": "/main/clmm-config",
    "CPMM_CONFIG": "/main/cpmm-config",
    "VERSION": "/main/version",
    
    # API v3 endpoints
    "CHECK_AVAILABILITY": "/v3/main/AvailabilityCheckAPI",
    "RPCS": "/main/rpcs",
    "INFO": "/main/info",
    "STAKE_POOLS": "/main/stake-pools",
    "CHAIN_TIME": "/main/chain-time",
    
    # Token endpoints
    "TOKEN_LIST": "/mint/list",
    "MINT_INFO_ID": "/mint/ids",
    "JUP_TOKEN_LIST": "https://tokens.jup.ag/tokens?tags=lst,community",
    
    # Pool endpoints
    "POOL_LIST": "/pools/info/list",
    "POOL_SEARCH_BY_ID": "/pools/info/ids",
    "POOL_SEARCH_MINT": "/pools/info/mint",
    "POOL_SEARCH_LP": "/pools/info/lps",
    "POOL_KEY_BY_ID": "/pools/key/ids",
    "POOL_LIQUIDITY_LINE": "/pools/line/liquidity",
    "POOL_POSITION_LINE": "/pools/line/position",
    
    # Farm endpoints
    "FARM_INFO": "/farms/info/ids",
    "FARM_LP_INFO": "/farms/info/lp",
    "FARM_KEYS": "/farms/key/ids",
    
    # Owner endpoints
    "OWNER_CREATED_FARM": "/create-pool/{owner}",
    "OWNER_IDO": "/main/ido/{owner}",
    "OWNER_STAKE_FARMS": "/position/stake/{owner}",
    "OWNER_LOCK_POSITION": "/position/clmm-lock/{owner}",
    
    # Other endpoints
    "IDO_KEYS": "/ido/key/ids",
    "SWAP_COMPUTE": "/compute/",
    "SWAP_TX": "/transaction/",
    "MINT_PRICE": "/mint/price",
    "MIGRATE_CONFIG": "/main/migrate-lp",
    "PRIORITY_FEE": "/main/auto-fee",
    "CPMM_LOCK": "https://dynamic-ipfs.raydium.io/lock/cpmm/position",
} 