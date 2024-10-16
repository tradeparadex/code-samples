# Paraclear Balance Checker

This repository contains a Python script designed to interact with a Starkware-based smart contract to retrieve balance and account information, including token and perpetual asset balances. Specifically, it retrieves data for USDC tokens and margin health checks for an account on Paradex

## Features

- Retrieves account value
- Checks account health (Initial Margin and Maintenance Margin)
- Displays token balance (USDC)
- Lists perpetual balances for available markets

## Prerequisites

- **Python 3.7+**
- **pip**: (Python package manager)
- **Starknet.py**: The script uses the `starknet_py` library to interact with the StarkNet blockchain.
- **Requests**: To fetch markets data from an API.
- **Rich**: For fancy terminal printing.

## Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the following environment variables:
   - `BASE_API_URL`: Base URL for the API
   - `FULL_NODE_URL`: URL of the StarkNet full node
   - `PARACLEAR_ADDRESS`: Address of the Paraclear contract
   - `USDC_TOKEN_ADDRESS`: Address of the USDC token contract
   - `PRDX_API_URL`: URL for the PRDX API
   - `L2_ADDRESS`: The StarkNet L2 address you want to check

   You can get these information from : 
    - `Production` : https://api.prod.paradex.trade/v1/system/config
    - `Testnet` : https://api.testnet.paradex.trade/v1/system/config

    From the json result, you should copy the value of : 
    - `starknet_gateway_url` to `STRK_API_URL`
    - `paradex api url` to `PRDX_API_URL`
    - `starknet_fullnode_rpc_url` to `FULL_NODE_URL`
    - `bridged_token > l2_token_address` to `USDC_TOKEN_ADDRESS`

    Example (Production) : 
    - `STRK_API_URL` = "https://paraclear-mainnet.starknet.io"
    - `PRDX_API_URL` = "https://api.prod.paradex.trade/v1"
    - `FULL_NODE_URL` = "https://juno.api.prod.paradex.trade/rpc/v0_7"
    - `PARACLEAR_ADDRESS` = "0x3ca9388f8d4e04adecbd7b06b9b24a33030a593522248a7bddd87afc0b61a0c"
    - `USDC_TOKEN_ADDRESS` = "0x7348407ebad690fec0cc8597e87dc16ef7b269a655ff72587dafff83d462be2"

## Usage

To run the script, use the following command:

```
python get_balance_onchain.py
```

Replace `get_balance_onchain.py` with the actual name of the Python file if it's different.

The script will output the account's balance information, including:
- Account value
- Account health status (Initial Margin and Maintenance Margin)
- USDC token balance
- Perpetual balances for each available market

## Customization

- To check a different account, modify the `L2_ADDRESS` environment variable or update the `get_balance_onchain()` function in the script.
- To add or remove markets, update the `get_markets_from_api()` function or modify the API endpoint it's calling.