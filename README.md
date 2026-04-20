# CCFeed

A Flask web app that stores and displays notes in a local SQLite database, served via a simple HTTP ingest API. Forked from ATCFeed (ATProto backend); CCFeed replaces the PDS dependency with local persistence.

**Live URL:** https://labnotes.jamnlx.jamnet  
**Dev source:** `~/dev/CCFeed` (GitHub: jamntoast-jf/CCFeed)  
**Prod:** `~/prod/lab/app/LabNoteFeed`

## Stack

| Layer | Tech |
|---|---|
| Web framework | Flask |
| Storage | SQLite (`/data/notes.db`) |
| Ingest | `POST /api/ingest` with `X-Api-Key` header |
| Pagination | Client-side offset pagination over full fetched set |
| Date filter | Monthly calendar widget — click a day to filter |
| Stats | Total posts, avg/day, top 5 days (clickable), avg/top cost (if present) |
| Styling | CSS custom properties, light/dark mode, responsive |
| Container | Python 3.12-slim + Gunicorn behind Traefik |

## Data Flow

Notes are written by the `claude-labnote-hook` stop hook (`~/bin/claude-labnote-hook`), which fires after each Claude Code session and POSTs the last user prompt + token cost to the ingest endpoint.

```
Claude Code session ends
  → claude-labnote-hook (Stop hook)
      → POST /api/ingest (X-Api-Key auth)
          → SQLite notes table
              → Flask feed renders from DB
```

## Project Structure

```
CCFeed/
├── app/
│   ├── __init__.py          # App factory; calls init_db on startup
│   ├── db.py                # SQLite backend (init_db, insert_note, fetch_notes)
│   ├── main/
│   │   ├── __init__.py      # Blueprint registration
│   │   └── routes.py        # Route handlers, stats, calendar, day filter, mobile detect
│   ├── api/
│   │   ├── __init__.py      # Blueprint registration
│   │   └── routes.py        # POST /api/ingest endpoint
│   ├── templates/
│   │   ├── base.html        # Layout, CSS vars, light/dark toggle, responsive rules
│   │   └── index.html       # Top panel (stats + cal side-by-side), feed, pagination
│   └── static/
│       └── style.css
├── tools/
│   └── migrate_from_pds.py  # One-time ATProto → SQLite migration (run inside container)
├── config.py                # Config class (reads DB_PATH, API_KEY, FEED_TITLE)
├── atcfeed.py               # Flask entry point
├── requirements.txt         # Flask, python-dotenv
├── Dockerfile               # python:3.12-slim + gunicorn
├── compose.yml              # Volume: ~/data/LabNoteFeed:/data; Traefik labels
├── .env                     # Credentials (not committed); see .env.example
├── .env.example             # Template for .env
└── .gitignore
```

## Configuration

All configuration is via environment variables in `.env`.

### App Variables

| Variable | Required | Description |
|---|---|---|
| `DB_PATH` | No | Path to SQLite DB file (default: `/data/notes.db`) |
| `API_KEY` | Yes | Secret key for ingest endpoint (`X-Api-Key` header) |
| `FEED_TITLE` | No | Title shown in the UI (default: `CCFeed`) |
| `SECRET_KEY` | No | Flask session secret (defaults to insecure dev value) |
| `FLASK_APP` | Dev | Set to `atcfeed.py` |
| `SUBDOMAIN` | Prod | Traefik subdomain (e.g. `labnotes`) |
| `DOMAIN_NAME` | Prod | Traefik domain (e.g. `jamnlx.jamnet`) |

### Hook Variables

Set these in `~/.claude/settings.json` → `env`:

| Variable | Description |
|---|---|
| `LABNOTE_API_KEY` | Must match `API_KEY` in container `.env` |
| `CCFEED_INGEST_URL` | Full ingest URL, e.g. `https://labnotes.jamnlx.jamnet/api/ingest` |

## Ingest API

```
POST /api/ingest
Headers: X-Api-Key: <API_KEY>
Body (JSON):
  text       string  required  note text
  service    string  optional  default "claude-code"
  tags       string  optional  comma-separated, e.g. "ai,claude,prompt"
  created_at string  optional  ISO 8601 UTC; defaults to now

Response 201:
  { "id": 123, "rkey": "20260420T153017994037-0aaa0f" }
```

## Running Locally

```bash
cd ~/dev/CCFeed
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set API_KEY, DB_PATH to a local path
flask run
```

Visit http://localhost:5000

## Production Deploy

Use the `/labnotefeed-deploy` skill, or manually:

```bash
# 1. Commit and push from dev
git -C ~/dev/CCFeed add -A && git -C ~/dev/CCFeed commit -m "message"
git -C ~/dev/CCFeed push origin master

# 2. Pull in prod
git -C ~/prod/lab/app/LabNoteFeed pull origin master

# 3. Rebuild if Dockerfile/requirements.txt changed
docker compose -f ~/prod/lab/compose.yml build labnotes

# 4. Restart
docker compose -f ~/prod/lab/compose.yml restart labnotes
```

## Migrating from ATProto PDS

Run inside the container (avoids root DB permission issues):

```bash
docker exec lab-labnotes-1 python3 /app/tools/migrate_from_pds.py \
  --db /data/notes.db \
  --pds-url https://jamntoast.com \
  --handle jamntoast.jamntoast.com \
  --password <app-password> \
  --collection com.labnote.note
```

Safe to re-run — uses `INSERT OR IGNORE`.

## Smoke Test

```bash
curl -sk -X POST https://labnotes.jamnlx.jamnet/api/ingest \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: <API_KEY>" \
  -d '{"text":"test note","service":"claude-code","tags":"test"}'
# → {"id": N, "rkey": "..."}
```

## Favicon

Drop `favicon.ico` into `app/static/` and restart. The app detects it at startup and adds the `<link rel="icon">` tag automatically.
