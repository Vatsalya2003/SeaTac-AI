import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { 
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  Download
} from 'lucide-react';
import { cn } from './ui/utils';
import { formatHour, isHourColumn } from '../format';

interface DataTableProps {
  data: any[];
  columns?: string[];
  title?: string;
  pageSize?: number;
  searchable?: boolean;
  sortable?: boolean;
  exportable?: boolean;
  /** the row the answer's headline is about (same object as in data), highlighted; none if undefined */
  highlightRow?: any;
}

type SortDirection = 'asc' | 'desc' | null;

// Search and the "Showing X of Y rows" line only for longer tables
const LONG_TABLE_ROWS = 25;

export function DataTableWithExport({ 
  data, 
  columns: providedColumns,
  title,
  pageSize = 5,
  searchable = true,
  sortable = true,
  exportable = true,
  highlightRow
}: DataTableProps) {
  // Extract columns from data if not provided
  const columns = providedColumns || (data.length > 0 ? Object.keys(data[0]) : []);
  
  // State management
  const [expanded, setExpanded] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Filter data based on search
  const filteredData = searchTerm
    ? data.filter(row =>
        columns.some(col => {
          const value = row[col];
          return value != null && String(value).toLowerCase().includes(searchTerm.toLowerCase());
        })
      )
    : data;

  // Sort data
  const sortedData = sortColumn && sortDirection
    ? [...filteredData].sort((a, b) => {
        const aVal = a[sortColumn];
        const bVal = b[sortColumn];
        
        // Handle null/undefined
        if (aVal == null) return sortDirection === 'asc' ? 1 : -1;
        if (bVal == null) return sortDirection === 'asc' ? -1 : 1;
        
        // Handle numbers
        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        }
        
        // Handle strings
        const aStr = String(aVal).toLowerCase();
        const bStr = String(bVal).toLowerCase();
        
        if (sortDirection === 'asc') {
          return aStr < bStr ? -1 : aStr > bStr ? 1 : 0;
        } else {
          return bStr < aStr ? -1 : bStr > aStr ? 1 : 0;
        }
      })
    : filteredData;

  // Preview the first rows; expanding reveals every filtered result.
  const startIndex = 0;
  const endIndex = expanded ? sortedData.length : pageSize;
  const paginatedData = sortedData.slice(0, endIndex);
  // keep the highlighted row visible in the short preview: shown after a "⋯" row if it would be hidden
  const pinnedRow = !expanded && highlightRow !== undefined && sortedData.includes(highlightRow)
    && !paginatedData.includes(highlightRow) ? highlightRow : undefined;

  // Handle sort
  const handleSort = (column: string) => {
    if (!sortable) return;
    
    if (sortColumn === column) {
      // Cycle through: asc -> desc -> null
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortColumn(null);
        setSortDirection(null);
      }
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // Export to CSV
  const exportToCSV = () => {
    const headers = columns.join(',');
    const rows = sortedData.map(row =>
      columns.map(col => {
        const value = isHourColumn(col) ? formatHour(row[col]) ?? row[col] : row[col];
        // Escape commas and quotes
        const escaped = String(value ?? '').replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(',')
    );
    
    const csv = [headers, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title || 'data'}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Format cell value
  // numbers are right-aligned; hours (00:00) are labels, left-aligned
  const isNumeric = (col: string) => !isHourColumn(col) && data.some(row => typeof row[col] === 'number');
  const formatValue = (value: any, col: string): string => {
    if (value == null) return 'No data';
    if (isHourColumn(col)) return formatHour(value) ?? String(value);  // 0-23 -> "00:00" … "23:00"
    if (typeof value === 'number') {
      const average = /^avg_|^average_/.test(col);
      return value.toLocaleString('en-US', {
        minimumFractionDigits: average ? 2 : 0,
        maximumFractionDigits: average ? 2 : Number.isInteger(value) ? 0 : 2,
      });
    }
    if (value instanceof Date) {
      return value.toLocaleString();
    }
    return String(value);
  };

  // Format column header
  const formatHeader = (col: string): string => {
    const labels: Record<string, string> = {
      aircraft_type_group: 'Aircraft type', weight_class_group: 'Weight class',
      avg_taxi_in_min: 'Avg. taxi-in (min)', avg_taxi_out_min: 'Avg. taxi-out (min)',
      avg_occupancy_sec: 'Avg. occupancy (sec)', avg_occupancy_min: 'Avg. occupancy (min)',
      avg_takeoff_delay_min: 'Avg. takeoff delay (min)', local_hour: 'Hour',
      off_block_hour: 'Off-block hour', max_aircraft_in_area: 'Peak aircraft',
      completed_operations: 'Completed operations', hour_rank: 'Rank',
    };
    if (labels[col]) return labels[col];
    return col
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="w-full space-y-4">
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div>
          {title && (
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          )}
          {data.length >= LONG_TABLE_ROWS && (
            <p className="text-sm text-gray-500 mt-1">
              Showing {sortedData.length ? startIndex + 1 : 0}–{Math.min(endIndex, sortedData.length)} of {sortedData.length} rows
            </p>
          )}
        </div>
        
        {exportable && data.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={exportToCSV}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
        )}
      </div>

      {/* Search Bar */}
      {searchable && data.length >= LONG_TABLE_ROWS && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search across all columns..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setExpanded(false);
            }}
            className="pl-10"
          />
        </div>
      )}

      {/* Table */}
      <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
        <Table className="query-data-table">
          <TableHeader>
            <TableRow className="bg-gray-50">
              {columns.map((col) => (
                <TableHead
                  key={col}
                  className={cn(
                    "font-semibold text-gray-700",
                    isNumeric(col) && "query-number",
                    sortable && "cursor-pointer select-none hover:bg-gray-100"
                  )}
                  onClick={() => handleSort(col)}
                >
                  <div className="flex items-center gap-2">
                    {formatHeader(col)}
                    {sortable && (
                      <span className="text-gray-400">
                        {sortColumn === col ? (
                          sortDirection === 'asc' ? (
                            <ArrowUp className="h-3.5 w-3.5" />
                          ) : (
                            <ArrowDown className="h-3.5 w-3.5" />
                          )
                        ) : (
                          <ArrowUpDown className="h-3.5 w-3.5" />
                        )}
                      </span>
                    )}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedData.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-center py-8 text-gray-500"
                >
                  {searchTerm ? 'No results found' : 'No data available'}
                </TableCell>
              </TableRow>
            ) : (
              [...paginatedData, ...(pinnedRow ? [null, pinnedRow] : [])].map((row, rowIndex) => row === null ? (
                <TableRow key="gap" className="query-row-gap" aria-hidden="true">
                  <TableCell colSpan={columns.length}>⋯</TableCell>
                </TableRow>
              ) : (
                <TableRow key={rowIndex} className={cn('hover:bg-gray-50', row === highlightRow && 'query-row-headline')}
                          aria-current={row === highlightRow ? 'true' : undefined}
                          title={row === highlightRow ? 'The row the answer refers to' : undefined}>
                  {columns.map((col) => (
                    <TableCell key={col} className={cn('text-gray-900', isNumeric(col) && 'query-number')}>
                      {formatValue(row[col], col)}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {sortedData.length > pageSize && (
        <Button
          variant="outline"
          size="sm"
          aria-expanded={expanded}
          onClick={() => setExpanded(value => !value)}
        >
          {expanded ? 'Show fewer rows' : `Show all ${sortedData.length} rows`}
        </Button>
      )}
    </div>
  );
}
