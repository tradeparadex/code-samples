# code-samples

Collection of Paradex code samples, snippets and benchmarks

## Examples

* [Go](go/README.md)
* [Java](java/README.md)
* [Python](python/README.md)
* [TypeScript](typescript/README.md)

## Benchmarks

### Order signing benchmarks

On MacBook Pro 2021, M1 Pro

```bash
Go: 1430 signs/sec - Go `gnark-crypto`
Java: 182 signs/sec - JVM `StarknetCurve` (1)
Java: 8 signs/sec - C++ `crypto-cpp`
Python: 182 signs/sec - Rust `starknet-crypto-py`
Python: 8 signs/sec - C++ `crypto-cpp-py`
TypeScript: 50 signs/sec - JavaScript `starknet.js`
```

(1) Reference: `java/paradex/StarknetCurve.groovy`

### Running on your machine

Examples and benchmarks for signing orders.

#### Python

To run it directly, you will need [Python 3.9+](https://www.python.org/downloads/).

```bash
cd python
python3.9 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python bench_order_sign.py
```

#### Go

```bash
cd go
go test -bench .
```

#### Java

```bash
cd java
groovy order.groovy bench
```

#### TypeScript

```bash
cd typescript
yarn run bench
```

## Ethereum and Starknet Keys

Ethereum (L1) private key is used to sign a message. Generated signature is
deterministic and can only be generated by the owner of the Ethereum private key.

This signature is then used to generate Starknet (L2) private key
(also referred to as Paradex private key).

Starknet (L2) private key can used to deduce Starknet public key.
L2 private key is also used to generate auth, onboarding and order signatures.

Auth endpoint also requires providing the Ethereum address which is derived
from the Ethereum private key in examples of some languages.

During the onboarding process, an Account Contract is deployed on Starknet
with the Starknet public key. This account contract address is used to identify
token and perpetual balances on chain.

On UI, after connecting with your Ethereum wallet, you will be able to click on
the truncated L2 address (top right) and view you L1 and L2 address. As well as copy the
L2 private key to clipboard.

To get complete understanding of this, please refer to [Onboarding & Wallets](https://docs.paradex.trade/getting-started/onboarding-and-wallets) section in Paradex documentation.
