# Examples - Java

## How to run

This example can be run directly.

### Requirements

* `PARADEX_ACCOUNT_ADDRESS`
* `PARADEX_PRIVATE_KEY`

### Running directly

All commands below are to be run from `examples/java` directory.

To run it directly, ensure [Groovy](https://groovy-lang.org/install.html) is installed.

Tested on `Groovy Version: 4.0.15 JVM: 21.0.1`

```bash
groovy auth.groovy
```

## Authentication

### Overview

What this example does:

* Retrieves a JWT to be used to make requests to private endpoints of the API

### Script notes

Refer to the `main` method under [auth.groovy](auth.groovy#L21) for the flow that consists of:

* Generating message hash and signature
* Getting a JWT from `/auth` endpoint
