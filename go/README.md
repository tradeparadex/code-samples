# Examples - Go

## How to run

This example can be run directly or with Docker.

### Requirements

You will need a private key of the Ethereum account that will control your Paradex account. Refer to [how to export an account's private key on MetaMask](https://support.metamask.io/hc/en-us/articles/360015289632-How-to-export-an-account-s-private-key).

### Required environment variables

* `ETHEREUM_PRIVATE_KEY`
* `PARADEX_PRIVATE_KEY`

### Running directly

All commands below are to be run from `go` directory.

To run it directly, ensure [Go 1.20.3+](https://go.dev/doc/install) is installed.

```bash
go run .
```

## Onboarding and Authentication

### Overview

What this example does:

* Generates and onboards a new Paradex account based on your Ethereum private key
* Retrieves a JWT to be used to make requests to private endpoints of the API
* Submits a new order to the private `POST /orders` endpoint using the JWT
* Makes a request to the private `GET /orders` endpoint using the JWT

### Script notes

Refer to the `main` function under [onboarding.go](onboarding.go#L180) for the main flow that consists of:

* Perform onboarding
* Authenticate and retrieve a JWT
* Calling multiple private endpoints
