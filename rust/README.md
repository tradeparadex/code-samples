# Examples - Rust

> [!WARNING]
> Examples utilize community SDK, use with caution

This is a simple example demonstrating how to use the Paradex API in Rust to:

- Connect to the testnet
- Get account information
- Subscribe to websocket feeds
- Place a market order

For more examples, visit [snow-avocado/paradex-rs/examples](https://github.com/snow-avocado/paradex-rs/tree/main/examples).

## Prerequisites

- Rust and Cargo installed
- A Paradex testnet private key

## Setup

1. Clone the repository
2. Add your Paradex testnet private key in `src/main.rs`:

```rust
const PARADEX_PRIVATE_KEY: &str = "<private key hex string>";
```

## Dependencies

The example uses the following crates (already specified in Cargo.toml):

- paradex = "0.1.3"
- tokio
- rust_decimal
- log
- simple_logger

## Running the example

1. Build and run the example:

```bash
cargo run
```

## What the example does

1. Connects to Paradex testnet
2. Retrieves and displays:
   - Account information
   - Balance
   - Positions
3. Sets up websocket subscriptions for:
   - Orders
   - Fills
   - Positions
   - Account updates
   - Balance updates
4. Places a market buy order for 0.001 BTC
5. Waits to receive websocket updates
6. Cleanly unsubscribes and closes connections

## Example output

You should see log output similar to:

```bash
INFO Account Information {...}
INFO Balance {...}
INFO Positions {...}
INFO Sending order {...}
INFO Order result {...}
INFO Received order update {...}
INFO Received fill {...}
```

## Note

This example uses the testnet environment. For production use, change `URL::Testnet` to `URL::Mainnet` and use your mainnet private key.

## Error handling

The example includes basic error handling. In a production environment, you should implement more robust error handling and retry logic.

## Contributing

Feel free to submit issues and enhancement requests!

## License

This example is released under the MIT License.
