# Examples

## How to run

This example can be run directly or with Docker.

### Requirements

You will need a private key of the Ethereum account that will control your Paradex account. Refer to [how to export an account's private key on MetaMask](https://support.metamask.io/hc/en-us/articles/360015289632-How-to-export-an-account-s-private-key).

Remember to replace the value of `ETHEREUM_PRIVATE_KEY` below with your own private key.

### Running directly

All commands below are to be run from `examples` directory.

To run it directly, you will need [Python 3.9+](https://www.python.org/downloads/).

```bash
brew install python3.9 # i.e. ensure python3.9 is available
python3.9 -m venv .venv # create Python 3.9 virtual env
source .venv/bin/activate
pip install -r requirements.txt # (.venv)
ETHEREUM_PRIVATE_KEY=private_key python onboarding/example.py # (.venv)
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
