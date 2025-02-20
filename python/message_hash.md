# StarkNet Message Hash

Following are the payloads that require a message hash for signature:

L1:

- Stark Key

L2:

- Onboarding
- Authentication
- New Order

## Message Hash

Inspired by [EIP-712](https://eips.ethereum.org/EIPS/eip-712),
(a standard for hashing and signing typed structured data)
the encoding of an off-chain message is defined as:

```python
signed_data = Enc["StarkNet Message", domain_separator, account, hash_struct(message)]
```

where:

- `domain_separator` is defined below.
- `account` is the StarkNet Account Contract for which the signing is executed
- `hash_struct(message)` is defined below.

**hash_struct:**

The message to be hashed is represented as a struct:

```js
struct MyStruct:
    member param1: felt
    member param2: felt*
   ...
end
```

and we define its encoding as

> hash_struct(message) = Enc[type_hash(MyStruct), Enc[param1], Enc[param2], ..., Enc[paramN]]

where type_hash is defined as in EIP-712 (but using selector instead of keccak):

> type_hash(MyStruct) = selector('MyStruct(params1:felt, params2:felt*,...)')

If MyStruct references other struct types (and these in turn reference even more struct types), then the set of referenced struct types is collected, sorted by name and appended to the encoding. See EIP-712 for more details

**domain_separator:**

The `domain_separator` is defined as the `hash_struct` of the `StarkNetDomain` struct:

```js
struct StarkNetDomain:
    member name: felt = 'Paradex'
    member version: felt = 1
    member chain_id: felt = 'PRIVATE_SN_POTC_SEPOLIA'
end
```

where `chain_id` is can be obtained calling `GET /system/config`

and the encoding:

> Enc[X=(x0, x1, ..., xn-1)] = Enc[Enc[x0], Enc[x1], ..., Enc[xn-1]] = h(....h(h(0,Enc[x0]), Enc[x1]), ...), n)

when X is an array, and:

> Enc[x] = x

when x is a felt, where

> h(a,b)

is the Pedersen hash on 2 field elements.

We also define

> selector(str) = starknet_keccak(str)

as defined in [starkware/starknet/abi.py](https://github.com/starkware-libs/cairo-lang/blob/master/src/starkware/starknet/public/abi.py)

### Message Payloads

**Stark Key (L1 Message):**

[EIP-712](https://eips.ethereum.org/EIPS/eip-712) message for L1 (Ethereum), the signed message is then used to generate StarkNet private Key.

> More details: [Account keys and addresses derivation standard](https://community.starknet.io/t/account-keys-and-addresses-derivation-standard/1230/1)

```js
message = { "action": "STARK Key" }
```

Types:

```js
EIP712Domain = [
  { "name": "name", "type": "string" },
  { "name": "version", "type": "string" },
  { "name": "chainId", "type": "uint256" }
]

Constant = [
  { "name": "action", "type": "string" }
]
```

**Onboarding (L2 Message):**

Message for L2 (StarkNet) onboarding, used to send message hash to get JWT token.

```js
message = { "action": "Onboarding" }
```

Types:

```js
Constant = [
  { "name": "action", "type": "felt" }
]
```

**Authentication (L2 Message):**

```js
message = {
  "method": "POST",
  "path": "/v1/auth",
  "body": "",
  "timestamp": UNIX_TIMESTAMP,
  "expiration": UNIX_TIMESTAMP
}
```

Types:

```js
Request = [
  { "name": "method", "type": "felt" },
  { "name": "path", "type": "felt" },
  { "name": "body", "type": "felt" },
  { "name": "timestamp", "type": "felt" },
  { "name": "expiration", "type": "felt" }
]
```

**New Order (L2 Message):**

```js
message = {
  "timestamp": UNIX_TIMESTAMP,
  "market": MARKET,
  "side": SIDE,
  "orderType": ORDER_TYPE,
  "size": SIZE,
  "price": PRICE,
}
```

Types:

```js
Order = [
  {  "name": "timestamp", "type": "felt" },
  { "name": "market", "type": "felt" },
  { "name": "side", "type": "felt" },
  { "name": "orderType", "type": "felt" },
  { "name": "size", "type": "felt" },
  { "name": "price", "type": "felt" }
]
```

**Common Types (L2):**

```js
StarkNetDomain = [
  { "name": "name", "type": "felt" },
  { "name": "chainId", "type": "felt" },
  { "name": "version", "type": "felt" }
]
```

## Message Hash Example

A complete python example with onboarding message payload can be found in [`message_hash.py`](message_hash.py):
