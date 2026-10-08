# Frontend - Airfield Data Intelligence

React-based conversational interface for querying airport operational data.

## Tech Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **UI Components:** shadcn/ui
- **Styling:** Tailwind CSS
- **Charts:** Chart.js + react-chartjs-2
- **Markdown:** react-markdown + remark-gfm

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

The app will be available at http://localhost:5173

## Configuration

Create `.env` in the frontend root:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── public/
│   └── aiportlogo.png        # Application logo
├── src/
│   ├── api/
│   │   └── query.ts          # Backend API client
│   ├── components/
│   │   ├── ui/               # shadcn/ui components
│   │   ├── ChatInput.tsx     # Message input component
│   │   ├── ChatMessage.tsx   # Message display component
│   │   ├── ChatSidebar.tsx   # Conversation sidebar
│   │   ├── ChatWelcome.tsx   # Welcome screen
│   │   └── ChartVisualization.tsx  # Chart rendering
│   ├── styles/               # Additional styles
│   ├── App.tsx               # Main application component
│   ├── main.tsx              # Application entry point
│   └── index.css             # Global styles
├── .env                      # Environment configuration
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## API Integration

The frontend communicates with the Flask backend via REST API:

```typescript
// src/api/query.ts
const response = await fetch(`${apiBase}/api/query`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: userMessage }),
});
```

### Expected Response Format

```json
{
  "success": true,
  "query_type": "taxi_in_by_type",
  "message": "Analysis shows B738 has the longest average taxi-in time...",
  "data": [...],
  "chart": {
    "type": "bar",
    "data": {...}
  }
}
```

## Components

### Core Components

| Component | Description |
|-----------|-------------|
| `App.tsx` | Main app with state management |
| `ChatInput.tsx` | Text input with send button |
| `ChatMessage.tsx` | Renders user/assistant messages |
| `ChatSidebar.tsx` | Conversation history sidebar |
| `ChartVisualization.tsx` | Renders Chart.js visualizations |

### UI Components (shadcn/ui)

Located in `src/components/ui/`, these are pre-built accessible components:

- `button.tsx`, `input.tsx`, `textarea.tsx`
- `card.tsx`, `dialog.tsx`, `dropdown-menu.tsx`
- `scroll-area.tsx`, `avatar.tsx`, `badge.tsx`
- And more...

## Styling

Uses Tailwind CSS with shadcn/ui design tokens. Global styles in `src/index.css`.

```tsx
// Example: Using Tailwind classes
<div className="flex items-center gap-4 p-6 bg-gray-50 rounded-lg">
  <Button variant="default">Send</Button>
</div>
```

## Troubleshooting

### Cannot connect to backend

1. Verify backend is running at http://localhost:8000
2. Check `VITE_API_BASE_URL` in `.env`
3. Check browser console for CORS errors

### Charts not rendering

```bash
# Install chart dependencies
npm install chart.js react-chartjs-2
```

### Build errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## License

MIT License - See root [README.md](../../README.md)