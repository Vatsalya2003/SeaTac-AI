import { useEffect, useRef, useState } from 'react';
import { Check, Copy, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { SourceBadge, badgeSource } from './AnswerSource';

/** What the app keeps from each API response (see App.tsx). Older saved chats may lack the newer fields. */
export interface AnswerMetadata {
  outputFormat?: string;
  outputConfidence?: number;
  queryType?: string;
  rowCount?: number;
  sqlSource?: string;
  metric?: string;
  sqlQueries?: string[];
  definition?: string;
  includedCount?: number;
  excluded?: Record<string, unknown>;
  ruleStatus?: string;  // 'confirmed' or 'provisional' (tested answers)
}

interface AnswerDetailsProps {
  content: string;           // the full answer text from the backend
  metadata?: AnswerMetadata;
  onClose: () => void;
}

const DETAILS_START = /\*\*(?:Sample|Definition)[^\n]*?:\*\*/;

/** The part of an answer that moves into this panel: Sample, Definition(s), notes and the footer line. */
export const detailsText = (content: string) => {
  const i = content.search(DETAILS_START);
  return i >= 0 ? content.slice(i) : '';
};

function splitDetails(text: string) {
  const parts = text.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
  const unwrap = (p: string) => p.replace(/^_+|_+$/g, '').trim();
  return {
    definitions: parts.filter(p => p.startsWith('**Definition')),
    samples: parts.filter(p => p.startsWith('**Sample')).map(p => p.replace(/^\*\*Sample:\*\*\s*/, '')),
    notes: parts.filter(p => /^_Note:/.test(p)).map(p => unwrap(p).replace(/^Note:\s*/, '')),
    footer: parts.filter(p => /^_Times are/.test(p)).map(unwrap),
  };
}

const formatCount = (v: unknown) => (typeof v === 'number' ? v.toLocaleString('en-US') : String(v));

// One clause per line, for reading only; the copy button copies the SQL exactly as it ran.
const readableSql = (sql: string) =>
  sql.replace(/\s+(FROM|WHERE|GROUP BY|ORDER BY|LEFT JOIN|JOIN|HAVING|LIMIT|UNION ALL)\b/g, '\n$1').trim();

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };
  return (
    <button type="button" className="sea-btn sea-btn-ghost sea-copy" onClick={copy} aria-label={label}>
      {copied ? <><Check aria-hidden="true" /> Copied</> : <><Copy aria-hidden="true" /> Copy</>}
    </button>
  );
}

export function AnswerDetails({ content, metadata, onClose }: AnswerDetailsProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const { definitions, samples, notes, footer } = splitDetails(detailsText(content));
  const excluded = Object.entries(metadata?.excluded ?? {}).filter(([, v]) => v !== 0 && v != null);
  const sql = metadata?.sqlQueries ?? [];

  // focus the close button; Esc closes; focus goes back to the Details link that opened the panel
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      opener?.focus?.();
    };
  }, [onClose]);

  return (
    <>
      <div className="sea-details-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="sea-details" role="dialog" aria-modal="true" aria-labelledby="answer-details-title"
             data-testid="answer-details">
        <header className="sea-details-head">
          <h2 id="answer-details-title">Answer details</h2>
          <button ref={closeRef} type="button" className="sea-icon-btn" onClick={onClose} aria-label="Close answer details">
            <X aria-hidden="true" />
          </button>
        </header>

        <div className="sea-details-body">
          <SourceBadge source={badgeSource(metadata?.sqlSource, content, metadata?.ruleStatus)} />

          {definitions.length > 0 && (
            <section>
              <h3>Definition</h3>
              {definitions.map((d, i) => (
                <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>
                  {d.replace(/^\*\*Definition \(([^)]*)\):\*\*\s*/, '**$1:** ').replace(/^\*\*Definition:\*\*\s*/, '')}
                </ReactMarkdown>
              ))}
            </section>
          )}

          {(samples.length > 0 || metadata?.includedCount != null) && (
            <section>
              <h3>Sample size</h3>
              {samples.map((s, i) => <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>{s}</ReactMarkdown>)}
              {metadata?.excluded && (
                excluded.length ? (
                  <dl className="sea-details-excluded">
                    {excluded.map(([reason, n]) => (
                      <div key={reason}><dt>Excluded: {reason}</dt><dd>{formatCount(n)}</dd></div>
                    ))}
                  </dl>
                ) : <p className="sea-details-muted">Nothing excluded.</p>
              )}
            </section>
          )}

          {(notes.length > 0 || footer.length > 0) && (
            <section>
              <h3>Notes</h3>
              <ul className="sea-details-notes">
                {notes.map((n, i) => <li key={i}><ReactMarkdown remarkPlugins={[remarkGfm]}>{n}</ReactMarkdown></li>)}
                {footer.map((f, i) => <li key={`f${i}`} className="sea-details-muted">{f}</li>)}
              </ul>
            </section>
          )}

          {sql.length > 0 && (
            <section>
              <h3>SQL used</h3>
              {sql.map((q, i) => (
                <div key={i} className="sea-details-sql">
                  <div className="sea-details-sql-head">
                    <span>{sql.length > 1 ? `Query ${i + 1} of ${sql.length}` : 'Query'}</span>
                    <CopyButton text={q} label={sql.length > 1 ? `Copy query ${i + 1}` : 'Copy SQL'} />
                  </div>
                  <pre><code>{readableSql(q)}</code></pre>
                </div>
              ))}
            </section>
          )}
        </div>
      </aside>
    </>
  );
}
