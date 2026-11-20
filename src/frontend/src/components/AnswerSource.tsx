import { BadgeCheck, FlaskConical, Sparkles } from 'lucide-react';
import { cn } from './ui/utils';

// Badge above each answer, from the backend's sql_source. Greetings ('system') and answers that
// couldn't be given ('none', or no sql_source) get no badge.
const SOURCE_BADGES: Record<string, { label: string; className: string; Icon: typeof BadgeCheck }> = {
  template: { label: 'Verified answer', Icon: BadgeCheck,
              className: 'answer-badge--verified' },
  provisional: { label: 'Tested, provisional rule', Icon: FlaskConical,
                 className: 'answer-badge--provisional' },
  ai_sql: { label: 'AI-generated, not yet verified', Icon: Sparkles,
            className: 'answer-badge--ai' },
};

// A tested answer whose rule the Port hasn't confirmed yet (Q3, Q7, Q10): the backend's rule_status says
// "provisional". Chats saved before rule_status existed fall back to the note text.
const PROVISIONAL_NOTE = /\bProvisional:|\bPROVISIONAL\b|PENDING PORT CONFIRMATION/;
export const badgeSource = (source: string | undefined, content: string, ruleStatus?: string) => {
  if (source !== 'template') return source;
  if (ruleStatus) return ruleStatus === 'provisional' ? 'provisional' : 'template';
  return PROVISIONAL_NOTE.test(content) ? 'provisional' : 'template';
};

export function SourceBadge({ source }: { source?: string }) {
  const badge = source ? SOURCE_BADGES[source] : undefined;
  if (!badge) return null;
  const { label, className, Icon } = badge;
  return (
    <div className={cn('answer-badge', className)} data-testid="answer-source-badge">
      <Icon className="answer-badge-icon" aria-hidden="true" />
      {label}
    </div>
  );
}
