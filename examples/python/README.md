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
#pre-req: create venv 
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
