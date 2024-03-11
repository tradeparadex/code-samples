import { getUnixTime } from "date-fns";
import {
  shortString,
  ec,
  typedData as starkTypedData,
  TypedData,
} from "starknet";

import { toQuantums } from "./conversions";

import {
  AuthRequest,
  buildAuthTypedData,
  buildOnboardingTypedData,
  buildOrderTypedData,
  UnixTime,
} from "./typed_data";
import { Account, SystemConfig } from "./types";

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

function signatureFromTypedData(account: Account, typedData: TypedData) {
  const msgHash = starkTypedData.getMessageHash(typedData, account.address);
  const { r, s } = ec.starkCurve.sign(msgHash, account.privateKey);
  return JSON.stringify([r.toString(), s.toString()]);
}

// Utility function to generate current and expiration timestamps
export function generateTimestamps(): {
  timestamp: UnixTime;
  expiration: UnixTime;
} {
  const dateNow = new Date();
  const dateExpiration = new Date(dateNow.getTime() + SEVEN_DAYS_MS);

  return {
    timestamp: getUnixTime(dateNow),
    expiration: getUnixTime(dateExpiration),
  };
}

export function signOnboardingRequest(
  config: SystemConfig,
  account: Account
): string {
  const typedData = buildOnboardingTypedData(config.starknet.chainId);
  const signature = signatureFromTypedData(account, typedData);
  return signature;
}

export function signAuthRequest(
  config: SystemConfig,
  account: Account
): {
  signature: string;
  timestamp: UnixTime;
  expiration: UnixTime;
} {
  const { timestamp, expiration } = generateTimestamps();

  const request: AuthRequest = {
    method: "POST",
    path: "/v1/auth",
    body: "", // Assuming no body is required for this request
    timestamp,
    expiration,
  };

  const typedData = buildAuthTypedData(request, config.starknet.chainId);
  const signature = signatureFromTypedData(account, typedData);

  return { signature, timestamp, expiration };
}

export function signOrder(
  config: SystemConfig,
  account: Account,
  orderDetails: Record<string, string>,
  timestamp: UnixTime
): string {
  const sideForSigning = orderDetails.side === "BUY" ? "1" : "2";

  const priceForSigning = toQuantums(orderDetails.price ?? "0", 8);
  const sizeForSigning = toQuantums(orderDetails.size, 8);
  const orderTypeForSigning = shortString.encodeShortString(orderDetails.type);
  const marketForSigning = shortString.encodeShortString(orderDetails.market);

  const message = {
    timestamp: timestamp,
    market: marketForSigning,
    side: sideForSigning,
    orderType: orderTypeForSigning,
    size: sizeForSigning,
    price: priceForSigning,
  };

  const typedData = buildOrderTypedData(message, config.starknet.chainId);
  const signature = signatureFromTypedData(account, typedData);

  return signature;
}
