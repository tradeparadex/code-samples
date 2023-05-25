# Onboarding and Authentication

## Overview

What this example does:

* Generates and onboards a new Paradex account based off your Ethereum private key
* Retrieves a JWT to be used to make requests to private endpoints of the API
* Makes a request to the private GET /orders endpoint using the JWT

## How to Run

This example can be run directly or with Docker.

### Requirements

You will need a private key of the Ethereum account that will control your Paradex account. Refer to [how to export an account's private key on MetaMask](https://support.metamask.io/hc/en-us/articles/360015289632-How-to-export-an-account-s-private-key).

Remember to replace the value of `ETHEREUM_PRIVATE_KEY` below with your own private key.

### Running directly

To run it directly, you will need [Python 3.9+](https://www.python.org/downloads/).

```bash
pip install -r requirements.txt
ETHEREUM_PRIVATE_KEY=private_key python example.py
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
