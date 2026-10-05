export function money(
  value: string | null,
  currency: string | null,
  includeCurrency = true,
): string {
  if (value === null) return "Not supplied";
  // Format the exact DECIMAL string without a floating-point conversion.
  const [whole, fractional = ""] = value.split(".");
  const amount = `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${fractional.padEnd(2, "0").slice(0, 2)}`;
  const extraPrecision = fractional.slice(2).replace(/0+$/, "");
  return `${includeCurrency && currency ? `${currency} ` : ""}${amount}${extraPrecision}`;
}
export function dateTime(value: string | null): string {
  if (!value) return "Not supplied";
  return (
    new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Kolkata",
    }).format(new Date(value)) + " IST"
  );
}
