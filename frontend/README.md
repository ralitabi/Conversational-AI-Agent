# Bradford Council AI Chatbot — Frontend

React 18 single-page application providing the chat interface for the Bradford Council AI assistant.

---

## Stack

- **React 18** with functional components and hooks
- **Tailwind CSS** for utility-first styling
- **Lucide React** for icons
- Communicates with the FastAPI backend at `http://localhost:8000/chat`

---

## Available Scripts

Run all commands from the `frontend/` directory.

### `npm start`

Starts the development server at [http://localhost:3000](http://localhost:3000).

Hot-reloads on file changes. Proxies API requests to the backend on port 8000.

### `npm run build`

Builds the app for production into the `build/` folder.

The backend (FastAPI) automatically serves this build when `frontend/build/` exists — so a production deployment only needs `python main.py`.

### `npm test`

Launches the test runner in interactive watch mode.

### `npm run eject`

**One-way operation — cannot be undone.** Exposes the underlying webpack/Babel config for full control.

---

## Key Components

| File | Purpose |
|------|---------|
| `src/App.js` | Root component, page layout |
| `src/components/ChatModal.jsx` | Chat UI: message bubbles, text input, option buttons, HTML card renderer |
| `src/data/homeData.js` | Homepage content (service list, descriptions) |

---

## Chat Response Types

The backend returns a `ChatResponse` with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `reply` | string | Plain text or HTML response to display |
| `input_type` | string \| null | `"options"` shows clickable buttons; null shows text input |
| `options` | array \| null | List of `{ id, label, value }` objects for option buttons |
| `messages` | array \| null | Multiple message bubbles to display in sequence |
| `session_id` | string | Echoed back to maintain session state |

HTML responses (rich cards for libraries, bin schedules, council tax info) are rendered with `dangerouslySetInnerHTML` — content is generated server-side and trusted.

---

## Connecting to the Backend

In development the frontend expects the backend at `http://localhost:8000`.

If you change the backend port, update the API base URL in `ChatModal.jsx`.

In production (Railway / Render / Fly.io) the React build is served by FastAPI itself from `frontend/build/` — no separate frontend server needed.
