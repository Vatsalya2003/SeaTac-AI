import { useState } from 'react';
import { Button } from './ui/button';
import { Copy, Check, BarChart3, Table as TableIcon, PanelRightOpen } from 'lucide-react';
import { SourceBadge, badgeSource } from './AnswerSource';
import type { AnswerMetadata } from './AnswerDetails';
import { cn } from './ui/utils';
import ChartVisualization from './ChartVisualization';
import { DataTableWithExport } from './DataTableWithExport';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './query-results.css';
import { headlineRow } from '../format';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date | string;
  chart?: any;
  data?: any[];
  metadata?: AnswerMetadata;
}

interface ChatMessageProps {
  message: Message;
  /** the question this answer replies to (used for titles when nothing better is known) */
  question?: string;
  /** opens the Answer details panel for this answer */
  onShowDetails?: () => void;
}

const GENERIC_TITLES = /^(seatac operations( analysis)?|query results)?$/i;

// Title for the answer's table and chart, from the question: the chart's own title (tested answers),
// else the question's name, else the question as asked. "(top 15)" is dropped for the table, which has every row.
function resultTitle(chartTitle: string | undefined, metric: string | undefined, question: string | undefined) {
  const fromChart = (chartTitle ?? '').trim();
  if (!GENERIC_TITLES.test(fromChart)) return fromChart.replace(/\s*\(top \d+\)\s*$/i, '');
  if (metric?.trim()) return metric.trim();
  const q = (question ?? '').replace(/\s+/g, ' ').trim().replace(/\?$/, '');
  return q ? (q.length > 80 ? `${q.slice(0, 79)}…` : q) : 'Results';
}

// "**Answer** (N rows):" label lines (templates and views modes). The "**Answer:**" sentence is kept.
const ROW_COUNT_LABEL = /^\*\*Answer\*\* \([\d,]+ rows?\)[^\n]*:[ \t]*\n?/gm;
const isTableLine = (line: string) => line.trimStart().startsWith('|');

// Removes the row-count labels. When the reply has data rows, also removes the last markdown table:
// it holds the same rows as message.data, which is shown below as the sortable, exportable data table.
// Every other table (e.g. Q4's arrivals/departures summary, Q7's by-taxiway table) stays in the text.
const HOURLY_ANSWERS = new Set(['Q2', 'Q3', 'Q10']);

const NUMBER_CELL = /^-?[\d,]+(\.\d+)?$/;
const cellsOf = (line: string) => line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());

// Marks number columns right-aligned in each markdown table (|---:|), labels left (|:---|).
function alignTableColumns(text: string): string {
  const lines = text.split('\n');
  for (let i = 1; i < lines.length; i++) {
    if (!/^\s*\|(\s*:?-+:?\s*\|)+\s*$/.test(lines[i]) || !isTableLine(lines[i - 1])) continue;
    let end = i + 1;
    while (end < lines.length && isTableLine(lines[end])) end++;
    const body = lines.slice(i + 1, end).map(cellsOf);
    const numeric = cellsOf(lines[i]).map((_, c) => body.length > 0
      && body.every(r => NUMBER_CELL.test(r[c] ?? '') || r[c] === 'No data') && body.some(r => NUMBER_CELL.test(r[c] ?? '')));
    lines[i] = '|' + numeric.map(n => (n ? '---:' : ':---')).join('|') + '|';
  }
  return lines.join('\n');
}

function answerMarkdown(markdown: string, hasData: boolean): string {
  const text = alignTableColumns(markdown.replace(ROW_COUNT_LABEL, ''));
  if (!hasData) return text;
  const lines = text.split('\n');
  let end = lines.length - 1;
  while (end >= 0 && !isTableLine(lines[end])) end--;
  if (end < 0) return text;
  let start = end;
  while (start > 0 && isTableLine(lines[start - 1])) start--;
  lines.splice(start, end - start + 1);
  return lines.join('\n');
}

const textOf = (node: any): string =>
  typeof node === 'string' || typeof node === 'number' ? String(node)
    : Array.isArray(node) ? node.map(textOf).join('')
    : node?.props?.children !== undefined ? textOf(node.props.children) : '';

// Markdown tables use the same style as the data table (query-results.css); numbers are right-aligned.
const markdownTables = {
  table: ({ node, ...props }: any) => (
    <div className="query-md-table">
      <table className="query-data-table" {...props} />
    </div>
  ),
  td: ({ node, children, ...props }: any) => (
    <td className={/^-?[\d,]+(\.\d+)?$/.test(textOf(children).trim()) ? 'query-number' : undefined} {...props}>
      {children}
    </td>
  ),
};

export function ChatMessage({ message, question, onShowDetails }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  // hourly answers (Q2 taxi-out by hour, Q3 movement area by hour, Q10 peak hours) open on the chart
  const [viewMode, setViewMode] = useState<'chart' | 'table'>(
    () => (HOURLY_ANSWERS.has(message.metadata?.queryType ?? '') && message.chart ? 'chart' : 'table'));
  const hasData = message.role === 'assistant' && !!message.data?.length;
  const tableTitle = resultTitle(message.chart?.title, message.metadata?.metric, question);
  const chartConfig = message.chart && GENERIC_TITLES.test((message.chart.title ?? '').trim())
    ? { ...message.chart, title: tableTitle } : message.chart;
  const detailStart = message.role === 'assistant'
    ? message.content.search(/\*\*(?:Sample|Definition)[^\n]*?:\*\*/)
    : -1;
  const details = detailStart >= 0 ? message.content.slice(detailStart) : '';
  const answer = detailStart >= 0 ? message.content.slice(0, detailStart) : message.content;

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (timestamp: Date | string) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  if (message.role === 'user') {
    return (
      <div className="sea-msg sea-msg-user" id={`msg-${message.id}`}>
        <div className="sea-bubble">{message.content}</div>
      </div>
    );
  }

  return (
    <article className="sea-msg sea-msg-assistant" id={`msg-${message.id}`} aria-label="Answer from SeaTac AI">
        <div className="sea-msg-meta">
          <span className="sea-msg-author">SeaTac AI</span>
          <time dateTime={new Date(message.timestamp).toISOString()}>{formatTime(message.timestamp)}</time>
          {onShowDetails && (details || message.metadata?.sqlQueries?.length) ? (
            <button type="button" className="sea-details-link" onClick={onShowDetails} aria-haspopup="dialog"
                    data-testid="answer-details-link">
              <PanelRightOpen aria-hidden="true" /> Details
            </button>
          ) : null}
        </div>

        <SourceBadge source={badgeSource(message.metadata?.sqlSource, message.content, message.metadata?.ruleStatus)} />

        {/* Markdown content */}
        <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed query-answer">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownTables}>
            {message.role === 'assistant' ? answerMarkdown(answer, hasData) : answer}
          </ReactMarkdown>
        </div>

        {/* Chart/Table Toggle for responses with both */}
        {message.role === 'assistant' && message.chart && message.data && message.data.length > 0 && (
          <div className="mt-4">
            <div className="flex items-center gap-2 mb-3">
              <Button
                variant={viewMode === 'chart' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('chart')}
                className="h-8 px-3 text-xs"
              >
                <BarChart3 className="h-3 w-3 mr-1.5" />
                Chart View
              </Button>
              <Button
                variant={viewMode === 'table' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('table')}
                className="h-8 px-3 text-xs"
              >
                <TableIcon className="h-3 w-3 mr-1.5" />
                Table View
              </Button>
            </div>

            {viewMode === 'chart' ? (
              <ChartVisualization chartConfig={chartConfig} insightsText={message.content} />
            ) : (
              <DataTableWithExport 
                data={message.data} 
                highlightRow={headlineRow(message.metadata?.queryType, message.data)}
                title={tableTitle}
                pageSize={5}
              />
            )}
          </div>
        )}

        {/* Chart Only (no table data) */}
        {message.role === 'assistant' && message.chart && (!message.data || message.data.length === 0) && (
          <div className="mt-4">
            <ChartVisualization chartConfig={chartConfig} insightsText={message.content} />
          </div>
        )}

        {/* Table Only (no chart) */}
        {message.role === 'assistant' && !message.chart && message.data && message.data.length > 0 && (
          <div className="mt-4">
            <DataTableWithExport 
              data={message.data} 
              highlightRow={headlineRow(message.metadata?.queryType, message.data)}
              title={tableTitle}
              pageSize={5}
            />
          </div>
        )}


        <div className="sea-msg-actions">
          <button type="button" className="sea-btn sea-btn-ghost sea-copy" onClick={copyToClipboard}>
            {copied ? <><Check aria-hidden="true" /> Copied</> : <><Copy aria-hidden="true" /> Copy</>}
          </button>
        </div>
    </article>
  );
}
