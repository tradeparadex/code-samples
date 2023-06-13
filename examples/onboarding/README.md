# Onboarding and Authentication

## Overview

What this example does:

* Generates and onboards a new Paradex account based off your Ethereum private key
* Retrieves a JWT to be used to make requests to private endpoints of the API
* Makes a request to the private GET /orders endpoint using the JWT

## Script notes

Refer to the `main` function under [onboarding/example.py](example.py#L323) for the main flow that consists of:

* Onboarding
* Getting a JWT
* Calling a private endpoint
