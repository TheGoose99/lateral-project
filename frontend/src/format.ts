export const money = new Intl.NumberFormat("ro-RO", {
  style: "currency",
  currency: "RON",
});

export function formatStatus(status: string): string {
  return status.replaceAll("_", " ");
}
