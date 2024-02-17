import { Bench } from 'tinybench';
import { shortString } from "starknet";

import { signOrder } from "./utils/signature";
import { Account, SystemConfig } from "./utils/types";


// Example usage of the Paradex API
(async () => {
  const apiBaseUrl = "https://api.testnet.paradex.trade/v1";
  const chainId = shortString.encodeShortString("PRIVATE_SN_POTC_SEPOLIA");
  const config: SystemConfig = {
    apiBaseUrl,
    starknet: { chainId },
  };

  const account: Account = {
    address: process.env.ACCOUNT_ADDRESS || "",
    publicKey: process.env.PUBLIC_KEY || "",
    privateKey: process.env.PRIVATE_KEY || "",
    ethereumAccount: process.env.ETHEREUM_ACCOUNT || "",
  };

  try {
    const bench = new Bench({ time: 1000 });

    bench
      .add('signs/sec', () => {
        const exampleOrder = {
          market: "ETH-USD-PERP",
          side: "SELL",
          type: "LIMIT",
          size: "10",
          price: "3292.04",
          instruction: "GTC",
        };
        const timestamp = Date.now();
        signOrder(config, account, exampleOrder, timestamp);
      })

    // Warmup to make results more reliable
    // ref: https://github.com/tinylibs/tinybench/pull/50
    await bench.warmup();
    await bench.run();

    console.table(bench.table());

  } catch (error) {
    console.error("BenchmarkError:", error);
  }
})();
