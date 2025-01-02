# Examples

## Commands

All commands below are to be run from `typescript` directory.

To run it directly, ensure [nvm 0.39+](https://github.com/nvm-sh/nvm) is installed.
Before proceeding, please be sure to have your Paradex Account (ACCOUNT_ADDRESS), your Ethereum Account and look up your Paradex Account PUBLIC_KEY[^1] and PRIVATE_KEY[^2]

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
---
[^1]: To find this value go to https://voyager.prod.paradex.trade/, search for your Paradex Account, and under Contract data choose the *getSigner* function from Read Contract
[^2]: This is available directly in Paradex. **PLEASE NEVER SHARE THIS WITH ANYONE EVEN IF THEY SAY THEY WORK FOR PARADEX**

