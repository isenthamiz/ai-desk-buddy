# Implemented Features

This is the source of truth for user-visible capabilities that exist in the
repository today. `features.md` remains the broader product roadmap, while
`milestones.md` tracks delivery sequence and incomplete milestone work.

Update this document in the same change that adds, materially changes, or removes
a feature. Describe shipped behavior rather than aspirations, note important
limitations, and link to the relevant milestone or protocol documentation when
useful.

## Backend and device communication

- FastAPI backend with a health endpoint and application lifecycle management.
- Bidirectional device connection over `/ws/device` using validated JSON messages.
- Simulator and physical-device registration, in-memory connected sessions, and
  safe rejection of invalid handshakes or unsupported messages.
- Shared buddy states and commands for state changes, display text, speech text,
  timers, and reminders. See `protocol.md` for the exact wire contract.

## Text conversation and AI tools

- Text conversations initiated by the simulator's temporary `USER_TEXT` input.
- OpenAI Responses API adapter behind a provider-neutral conversation interface.
- Bounded, per-device in-memory conversation history.
- Visible `THINKING` → `SPEAKING` → `IDLE` interaction flow, with a recoverable
  error response when the AI provider is unavailable or misconfigured.
- Deterministic tool registry used by the AI layer for timers, reminders, weather,
  and Todoist actions.

## Timers

- Start and cancel one backend-authoritative timer per connected device through AI
  tools or documented physical button events.
- Device-side countdown presentation driven by timer protocol messages.
- Completion flow with alert state, display text, and speech text.
- Timers are currently unnamed, in memory, and do not survive a backend restart or
  device disconnect. Pause/resume and Pomodoro workflows are not backend features.

## Reminders

- Create relative or absolute one-shot reminders and cancel them through AI tools.
- Supabase persistence with timezone-aware due times normalized to UTC. Without
  Supabase configuration reminders fall back to memory and do not survive restart.
- Restore pending reminders after a backend restart.
- Defer notifications while the owning device is offline and deliver them after it
  reconnects.
- Reminder alerts use the shared alert, display, and speech message flow.
- Recurrence, snoozing, and a reminder-management UI are not implemented.

## Weather

- Optional weather tool for current, today, and tomorrow conditions at one
  backend-configured location.
- Provider-neutral service with an Open-Meteo adapter and a ten-minute in-memory
  cache.
- Graceful configuration/provider failures and output through the existing
  conversation display and speech flow.
- Free-form locations, automatic location detection, scheduled reports, and severe
  weather alerts are not implemented.

## Todoist

- Optional single-user Todoist integration configured with a personal API token.
- Create Inbox tasks, list up to five today/overdue/upcoming tasks, and complete a
  task by exact Todoist ID through deterministic AI tools.
- Provider-neutral service and Todoist API v1 adapter.
- OAuth, project/label management, editing, deletion, background synchronization,
  and Todoist-driven device alerts are not implemented.

## Private Obsidian retrieval

- Optional `notes:` request path that bypasses OpenAI tools, conversation requests,
  and cloud conversation history.
- Standalone localhost `note-server` process protected by a shared bearer token.
  The main backend holds no vault or Supabase configuration and receives
  only final answers and citations.
- Deterministic Markdown chunking with live local keyword scanning. OpenAI creates
  embeddings and generates answers from the selected passages.
- Periodic hash reconciliation on startup and at a configurable interval; only new
  or changed chunks are re-embedded and deleted chunks are removed remotely.
- No local notes database. A separate Supabase metadata table stores paths, headings,
  chunk positions, hashes, and opaque IDs; plaintext note content remains in Obsidian.
- Supabase pgvector storage contains the owner identifier, opaque chunk IDs, content
  hashes, and embeddings. Query embeddings are sent to Supabase for similarity
  search and remain sensitive derived data.
- Results include Obsidian-style source citations. Vault exclusions and resolved-
  path checks prevent configured private folders and outside symlinks from indexing.
- Requires running both backend processes, manual Supabase migration/configuration,
  an OpenAI API key, and a model supporting 768-dimensional embedding output.
  OpenAI receives plaintext chunks during indexing, plus the question and selected
  passages during answer generation.
  Capture, filesystem-event watching, attachments, local-only vector storage, and
  automatic reconfiguration are not implemented.

## Desktop simulator

- Visual 240×240 circular buddy display with animated eyes, expressions, blinking,
  gaze, and lightweight idle motion.
- Manual state, face, timer, notification, presence, action-button, and text-input
  controls for development.
- Reconnecting WebSocket client that uses the same public protocol as firmware.
- Local timer and notification presentation for offline visual testing.
- Audio capture and playback are not implemented.

## ESP32 firmware

- PlatformIO/Arduino firmware for the currently available `esp32dev` board.
- Wi-Fi and reconnecting WebSocket connection using the shared device protocol.
- SSD1306 display abstraction with face/state, timer, and alert rendering.
- Debounced active-low buttons for timer duration selection, start, cancel, and
  alert acknowledgement.
- General display/speech/reminder content rendering and physical end-to-end
  verification remain incomplete, so Milestone 5 is still in progress.

## Buddy Control Center

- Standalone Expo SDK 57 application using React Native, TypeScript, Expo Router,
  and React Native Web from one shared codebase.
- Responsive web layout and native iPhone-compatible interface.
- Backend health, device connection, device type, and current Buddy state display.
- Start and cancel the connected device's backend-authoritative timer.
- List, create, and cancel durable reminders, including while the device is offline.
- Send text through the same conversation flow used by simulator text input.
- Client-facing REST endpoints remain separate from the device WebSocket protocol,
  with explicitly configured development CORS origins for Expo web.
- The initial version targets one configured device ID (`simulator-001` by default),
  polls for updates, has no authentication, and is intended only for trusted local
  development. A physical phone requires the backend computer's LAN address.
  The development iOS configuration permits local cleartext HTTP and must move to
  authenticated HTTPS before distribution.
  Remote access, authentication, multiple-device selection, App Store packaging,
  and broader settings are not implemented.
