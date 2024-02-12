/** Unix time in seconds
 * @example 1657627258
 */
export type UnixTime = number;

const DOMAIN_TYPES = {
  StarkNetDomain: [
    { name: "name", type: "felt" },
    { name: "chainId", type: "felt" },
    { name: "version", type: "felt" },
  ],
};

export function buildParadexDomain(starknetChainId: string) {
  return {
    name: "Paradex",
    chainId: starknetChainId,
    version: "1",
  };
}

export function buildOnboardingTypedData(starknetChainId: string) {
  const paradexDomain = buildParadexDomain(starknetChainId);
  return {
    domain: paradexDomain,
    primaryType: "Constant",
    types: {
      ...DOMAIN_TYPES,
      Constant: [{ name: "action", type: "felt" }],
    },
    message: {
      action: "Onboarding",
    },
  };
}

export interface AuthRequest extends Record<string, unknown> {
  method: string;
  path: string;
  body: string;
  timestamp: UnixTime;
  expiration: UnixTime;
}

export function buildAuthTypedData(
  message: Record<string, unknown>,
  starknetChainId: string
) {
  const paradexDomain = buildParadexDomain(starknetChainId);
  return {
    domain: paradexDomain,
    primaryType: "Request",
    types: {
      ...DOMAIN_TYPES,
      Request: [
        { name: "method", type: "felt" }, // string
        { name: "path", type: "felt" }, // string
        { name: "body", type: "felt" }, // string
        { name: "timestamp", type: "felt" }, // number
        { name: "expiration", type: "felt" }, // number
      ],
    },
    message,
  };
}

export function buildOrderTypedData(
  message: Record<string, unknown>,
  starknetChainId: string
) {
  const paradexDomain = buildParadexDomain(starknetChainId);
  return {
    domain: paradexDomain,
    primaryType: "Order",
    types: {
      ...DOMAIN_TYPES,
      Order: [
        { name: "timestamp", type: "felt" }, // UnixTimeMs; Acts as a nonce
        { name: "market", type: "felt" }, // 'BTC-USD-PERP'
        { name: "side", type: "felt" }, // '1': 'BUY'; '2': 'SELL'
        { name: "orderType", type: "felt" }, // 'LIMIT';  'MARKET'
        { name: "size", type: "felt" }, // Quantum value
        { name: "price", type: "felt" }, // Quantum value; '0' for Market order
      ],
    },
    message,
  };
}
