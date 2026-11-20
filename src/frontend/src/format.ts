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

// The row each tested answer's headline sentence is about (templates.py picks it the same way: the first row,
// in data order, with the highest value, or rank 1 for Q10). Other answers have no headline row.
const HEADLINE_ROW: Record<string, { column: string; pick: 'max' | 'min' }> = {
  Q1: { column: 'avg_taxi_in_min', pick: 'max' },       // "Longest average taxi-in: …"
  Q2: { column: 'avg_taxi_out_min', pick: 'max' },      // "Longest hour: …"
  Q3: { column: 'max_aircraft_in_area', pick: 'max' },  // "Busiest: the … hour"
  Q7: { column: 'flights', pick: 'max' },               // "Most used taxiway section: …"
  Q9: { column: 'total_operations', pick: 'max' },      // "Most used runway: …"
  Q10: { column: 'hour_rank', pick: 'min' },            // "Busiest hour: …"
};

export function headlineRow(questionId: string | undefined, rows: any[] | undefined): any | undefined {
  const rule = questionId ? HEADLINE_ROW[questionId] : undefined;
  if (!rule || !rows?.length) return undefined;
  let best: any;
  for (const row of rows) {
    const v = row?.[rule.column];
    if (typeof v !== 'number') continue;
    if (best === undefined || (rule.pick === 'max' ? v > best[rule.column] : v < best[rule.column])) best = row;
  }
  return best;
}
