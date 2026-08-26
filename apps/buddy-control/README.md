# Buddy Control

Universal Expo application for controlling AI Desk Buddy from a browser, iPhone,
or Android device. The app talks to the FastAPI control API; it never connects
directly to the simulator or firmware WebSocket.

## Requirements

- Node.js 22.13 or newer
- npm
- AI Desk Buddy backend running and reachable from the client device

## Install

```bash
npm install
cp .env.example .env.local
```

`EXPO_PUBLIC_BUDDY_API_URL` defaults to `http://127.0.0.1:8000`. Keep that value
for browser or iOS Simulator development on the backend Mac. For a physical
iPhone, replace it with the backend Mac's LAN address, such as
`http://192.168.1.20:8000`, and run the backend with `--host 0.0.0.0`.

## Run on the web

Start the backend and simulator, then run:

```bash
npm run web
```

Expo serves the app at `http://localhost:8081` by default. The backend permits
that development origin through `BUDDY_CONTROL_ALLOWED_ORIGINS`.

## Run on iPhone

SDK 57 targets development builds for current native development. On a Mac with
Xcode, connect an iPhone or start the iOS Simulator and run:

```bash
npx expo run:ios
```

For a physical phone, the phone and backend Mac must be on the same trusted
network. The current backend is unauthenticated and uses HTTP, so it must not be
exposed to the public internet. The development app temporarily permits cleartext
HTTP for this local workflow; replace it with authenticated HTTPS and remove
`NSAllowsArbitraryLoads` before any production or App Store build.

## Checks

```bash
npm run typecheck
npm run lint
npm run export:web
```
