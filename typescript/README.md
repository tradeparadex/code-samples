# Examples

## Commands

All commands below are to be run from `typescript` directory.

To run it directly, ensure [nvm 0.39+](https://github.com/nvm-sh/nvm) is installed.

Environment variables:

```bash
export ACCOUNT_ADDRESS=
export PUBLIC_KEY=
export PRIVATE_KEY=
export ETHEREUM_ACCOUNT=
```

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install
yarn install
yarn run app
yarn run bench
```

## Benchmarks

```bash
┌─────────┬─────────────┬─────────┬───────────────────┬──────────┬─────────┐
│ (index) │ Task Name   │ ops/sec │ Average Time (ns) │ Margin   │ Samples │
├─────────┼─────────────┼─────────┼───────────────────┼──────────┼─────────┤
│ 0       │ 'signs/sec' │ '50'    │ 19777384.0392157  │ '±0.28%' │ 51      │
└─────────┴─────────────┴─────────┴───────────────────┴──────────┴─────────┘
```
