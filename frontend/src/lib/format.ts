const SYMBOL: Record<string, string> = { USD: "$", INR: "₹", EUR: "€", GBP: "£" };

/** minor units (paise / cents) -> a display string. */
export function money(amountMinor: number, currency: string): string {
  const major = amountMinor / 100;
  const sym = SYMBOL[currency] ?? currency + " ";
  return `${sym}${major.toLocaleString(undefined, { minimumFractionDigits: major % 1 ? 2 : 0 })}`;
}

/** display string -> minor units. Returns null if not a valid non-negative number. */
export function toMinor(value: string): number | null {
  const n = Number(value.replace(/[^0-9.]/g, ""));
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 100);
}
