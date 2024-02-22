# Examples

## How to run

This example can be run directly or with Docker.

### Requirements

You will need a private key of the Ethereum account that will control your Paradex account. Refer to [how to export an account's private key on MetaMask](https://support.metamask.io/hc/en-us/articles/360015289632-How-to-export-an-account-s-private-key).

Remember to replace the value of `ETHEREUM_PRIVATE_KEY` below with your own private key.

### Running directly

All commands below are to be run from `examples` directory.

To run it directly, ensure [Python 3.9+](https://www.python.org/downloads/) is installed.

```bash
python3.9 -m venv .venv # create Python 3.9 virtual env
source .venv/bin/activate
pip install -r requirements.txt # (.venv)
ETHEREUM_PRIVATE_KEY=private_key python onboarding.py # (.venv)
```

#### Retrieving L2 Private Key

In order to fetch the L2 account details against the given L1 / Ethereum private key, you can run below script

```bash
# pre-req: create venv
ETHEREUM_PRIVATE_KEY=private_key python fetch_l2_account_details.py
```

### Running with Docker

Make sure you have pre-installed [Docker](https://docs.docker.com/get-docker/).

Build the Docker image and run the Docker container.

```bash
docker build -t example .
docker run -it --rm \
  -e ETHEREUM_PRIVATE_KEY=private_key \
  example
```

## Onboarding and Authentication

### Overview

What this example does:

* Generates and onboards a new Paradex account based off your Ethereum private key
* Retrieves a JWT to be used to make requests to private endpoints of the API
* Makes a request to the private GET /orders endpoint using the JWT

### Script notes

Refer to the `main` function under [onboarding.py](onboarding.py#L180) for the main flow that consists of:

* Onboarding
* Getting a JWT
* Calling a private endpoint

### Using L2 credentials to authenticate with the API.
Once you have onboarded, if you would rather use your L2 information directly, be sure to skip over the `Initialize Ethereum` account and `Generate Paradex account` functions in the script. If you simply plug in your L2 private key in place of the `eth_private_key_hex` variable, you will actually be generating a separate account that isn't actually usable.

Why?

These functions are a part of a deterministic process to generate L2 data. When you use your L1 private key (as expected), it will generate the same L2 data to be used every time. 
However, if you give the program something different it's going to generate  _separate_ L2 data which is going to point to a separate account. Any info you try to pull this way will show as if the account is completely blank.

That being said, once you've onboarded and generated the L2 data (even just from the UI), you can plug the L2 account and private key directly into the other functions calling private endpoints which will authenticate correctly just as if you had started with the L1 private key.

## Withdraw

### Overview

What this example does:

* Withdraws from Paradex (Paraclear Contract) to L1 token bridge contract
* Waits for transaction to be accepted on L1 (Ethereum)
* Withdraw from L1 token bridge contract to L1 wallet

### Script notes

Refer to the `main` function under [withdraw.py](withdraw.py#L111) for the main flow that consists of:

* Withdraw from Paradex (Paraclear Contract)
* Wait for transaction to be accepted on L1
  * *Note: Poll for transaction receipt can take up to 12 hours*
* Withdraw from L1 bridge

*Note: L1 gas fees may fluctuate, adjust `maxFeePerGas` and `maxPriorityFeePerGas` accordingly*

#### Ethereum (L1) Contract ABIs

ABI for any L1 contract can be sourced from Etherscan. Steps:

1. Go to [Goerli Etherscan](https://goerli.etherscan.io/)
2. Search for contract address (or `https://goerli.etherscan.io/address/<address>`)
3. Click on `Contract` tab
4. Click on `Read as Proxy` tab
5. Click on ABI for the implementation contract link
6. Navigate to `Contract ABI` section
7. Save the ABI to a JSON file

*Note: Contracts must be deployed with source code verification on Etherscan.*

## Transfer (L2)

Script to transfer all USDC tokens from one L2 account to another L2 account on Paradex (Paraclear Contract).

```bash
# pre-req: create venv
OLD_PARADEX_ACCOUNT_PRIVATE_KEY=private_key NEW_PARADEX_ACCOUNT_PRIVATE_KEY=private_key python transfer_l2_usdc.py
```

### Overview

What this example does:

* Withdraws from Paradex (Paraclear Contract) to L2 Contract (old)
* Triggers transfer of USDC tokens from L2 Contract (old) to L2 Contract (new)
* Deposits to Paradex (Paraclear Contract) from L2 Contract (new)

### Script notes

* Ensure both accounts have previously onboarded via the onboarding example or UI:
  * `OLD_PARADEX_ACCOUNT_PRIVATE_KEY` (L2 Private Key of old account)
  * `NEW_PARADEX_ACCOUNT_PRIVATE_KEY` (L2 Private Key of new account)
* Remove default amount from [transfer_l2_usdc.py](transfer_l2_usdc.py#L29) to transfer all USDC balance
  * Default: 100 USDC
* **Please note:**
  * Script only transfers free USDC tokens
  * It will **not** realize any PnLs or close any open positions
