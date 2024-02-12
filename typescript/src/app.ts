import {
  authenticate,
  createOrder,
  getAccountInfo,
  getOpenOrders,
  listAvailableMarkets,
  onboardUser,
} from "./utils/api";
import { Account, SystemConfig } from "./utils/types";
import { shortString } from "starknet";

// Example usage of the Paradex API
(async () => {
  // TODO: Get from /system/config
  const apiBaseUrl = "https://api.testnet.paradex.trade/v1";
  const chainId = shortString.encodeShortString("PRIVATE_SN_POTC_SEPOLIA");
  const config: SystemConfig = {
    apiBaseUrl,
    starknet: { chainId },
  };

  // TODO: Add key derivation
  const account: Account = {
    address: process.env.ACCOUNT_ADDRESS || "",
    publicKey: process.env.PUBLIC_KEY || "",
    privateKey: process.env.PRIVATE_KEY || "",
    ethereumAccount: process.env.ETHEREUM_ACCOUNT || "",
  };

  try {
    await onboardUser(config, account);
    account.jwtToken = await authenticate(config, account);
    const exampleOrder = {
      market: "ETH-USD-PERP",
      side: "SELL",
      type: "LIMIT",
      size: "10",
      price: "3292.04",
      instruction: "GTC",
    };
    await createOrder(config, account, exampleOrder);
    await getOpenOrders(config, account);
    await getAccountInfo(config, account);
    await listAvailableMarkets(config);
  } catch (error) {
    console.error("AppError:", error);
  }
})();
