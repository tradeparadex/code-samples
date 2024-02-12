import BigNumber from "bignumber.js";

/**
 * Convert to quantums rounding final number down.
 *
 * @param amount Amount in human numbers
 * @param precision How many decimals the target contract works with
 * @returns Quantum value
 *
 */
export function toQuantums(
  amount: BigNumber | string,
  precision: number
): string {
  const bnAmount = typeof amount === "string" ? BigNumber(amount) : amount;
  const bnQuantums = bnAmount.dividedBy(`1e-${precision}`);
  return bnQuantums.integerValue(BigNumber.ROUND_FLOOR).toString();
}
