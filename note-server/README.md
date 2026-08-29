# AI Desk Buddy Private Notes Server

This standalone localhost service owns all access to the Obsidian vault, OpenAI note
processing and separate Supabase note-metadata and vector tables. Paths, headings,
positions, and hashes are stored remotely; plaintext note content is not. The main
Buddy backend receives only final answers and citations.

Copy `.env.example` to `.env` and apply `supabase/notes.sql` in the Supabase SQL
editor. Set `OPENAI_API_KEY`; OpenAI receives note chunks for embedding and receives
the question plus selected passages when generating an answer. The whole vault is
not sent in one request, but this is not a local-only privacy design.

Install and run the service:

```bash
uv sync
uv run uvicorn aideskbuddy_notes.main:app --host 127.0.0.1 --port 8010
```

Never bind this service to `0.0.0.0`. The Supabase `sb_secret_...` key and vault path
belong only in `note-server/.env`; an `sb_publishable_...` key will not work because
the note table is server-only. Put the same `NOTES_SERVICE_TOKEN` value in the main
backend as `BUDDY_NOTES_SERVICE_TOKEN`, alongside
`BUDDY_NOTES_SERVICE_URL=http://127.0.0.1:8010`.
