import { ArrowUpRight } from 'lucide-react';

// The Port's priority questions. Each one routes to a tested answer (checked against intent.py's keywords).
export const SUGGESTED_QUESTIONS = [
  'Average taxi-in time by aircraft type',
  'Taxi-out time by hour of day',
  'Busiest hours of the day',
  'Runway occupancy for arrivals and departures',
  'Average takeoff delay',
  'Time from wheels-down to parking',
  'Taxi times by weight class',
  'Most used taxiways',
  'Takeoffs and landings by runway',
];

interface ChatWelcomeProps {
  onAsk: (question: string) => void;
  disabled?: boolean;
}

export function ChatWelcome({ onAsk, disabled = false }: ChatWelcomeProps) {
  return (
    <section className="sea-welcome" aria-labelledby="welcome-title">
      <h2 id="welcome-title">Ask about SeaTac airfield operations</h2>
      <p>Taxi times, runway use, delays and peak hours, from the Port’s {'August\u00a08,\u00a02025'} data.</p>
      <ul className="sea-chips" aria-label="Suggested questions">
        {SUGGESTED_QUESTIONS.map((q) => (
          <li key={q}>
            <button type="button" className="sea-chip" onClick={() => onAsk(q)} disabled={disabled}>
              <span>{q}</span>
              <ArrowUpRight aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
