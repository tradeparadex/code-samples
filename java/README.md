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
groovy order.groovy
```

## Authentication and Order Creation

### Overview

What this example does:

* Retrieves a JWT to be used to make requests to private endpoints of the API
* Creates a new market order using the JWT token from previous step

### Script notes

Refer to the `main` method under [order.groovy](order.groovy#L29) for the flow that consists of:

* Generating message hash and signature
* Getting a JWT from `GET /auth` endpoint
* Creating order using `POST /orders` endpoint
* Run benchmarks using `groovy order.groovy bench`

### Benchmarks

```bash
Total time for 2000 orders: 10.979s
Average time per order: 5.4895ms
Result: 182.1659531834 signs/sec
```
