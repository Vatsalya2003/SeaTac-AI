// Shared display formatting for answer tables and charts.

/** Columns that hold an hour of the day (0-23) in the API data. */
const HOUR_COLUMNS = new Set(['local_hour', 'off_block_hour', 'selection_hour', 'hour']);

export const isHourColumn = (column: string) => HOUR_COLUMNS.has(column);

/** 0-23 (number or digit string) -> "00:00" … "23:00"; anything else -> null. */
export function formatHour(value: unknown): string | null {
  const n = typeof value === 'number' ? value
    : typeof value === 'string' && /^\s*\d{1,2}\s*$/.test(value) ? Number(value) : NaN;
  return Number.isInteger(n) && n >= 0 && n <= 23 ? `${String(n).padStart(2, '0')}:00` : null;
}
