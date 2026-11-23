# babakoto-web

Next.js playground: a mic button, live captions for both sides and per-reply latency.

```sh
# needs LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in the environment (see .env.example)
pnpm --filter babakoto-web dev        # http://localhost:3000
pnpm --filter babakoto-web test       # unit tests
pnpm --filter babakoto-web build && pnpm --filter babakoto-web e2e
```

- `POST /api/token` mints a 10-minute LiveKit token for a random room. The agent worker joins
  every new room automatically. There is no user login yet (arrives with the dashboard).
- Captions come from LiveKit's `lk.transcription` text streams. User speech has a transcribed
  track id attribute; everything else is the agent.
- Latency comes from the agent's `babakoto.latency` data messages: end of your speech to the
  first agent audio, as LiveKit measures it in the call.
- UI text is English for now. Malagasy UI strings need native review first (ADR-0022).
- End-to-end tests need a browser. If the bundled one cannot run on your system (NixOS), set
  `PLAYWRIGHT_CHROME_PATH` to a system Chrome.

Not yet verified against a live LiveKit server and agent.
