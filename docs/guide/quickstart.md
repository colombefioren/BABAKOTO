# Run the local playground

Install Docker with Compose, Node.js, pnpm, uv and just. Run these commands on
the machine that will host the playground.

```sh
git clone https://github.com/colombefioren/BABAKOTO.git && cd BABAKOTO
just dev
just up cpu
```

After `just dev`, set `GLADIA_API_KEY` and the LLM provider settings in the ignored
`.env` before starting the CPU profile. The generated file also holds the local
LiveKit, service and operator credentials. The CPU profile sends microphone
audio to Gladia and plays a synthetic test tone by default.
[Gladia data retention](https://eu1.docs.gladia.io/data/retention/)

Open [localhost:3000](http://localhost:3000) on the host. Sign in as `babakoto` with
the `WEB_PLAYGROUND_PASSWORD` from `.env`. Allow microphone access, select
**Start conversation** and watch for captions. Run `just down` to stop the local
services. It keeps the database volume and downloaded caches.

## Run speech recognition locally

Install an NVIDIA driver and the NVIDIA Container Toolkit. Accept Sunflower's
gated model terms with your Hugging Face account. Set `HF_TOKEN` and an exact
`SUNFLOWER_MODEL_REVISION` in `.env`. Use `just down` and then `just up gpu` to
switch profiles. The GPU profile uses local Sunflower recognition by default.
It still sends transcribed text to the selected LLM. Choose a local
OpenAI-compatible endpoint if your deployment needs a local language model.

## Open the agent dashboard

Run `just up-dashboard` to start the private API and PostgreSQL. Open **Agent
configurations** from the playground. The dashboard also works independently
of the speech services.

[Configuration reference](https://github.com/colombefioren/BABAKOTO/blob/main/.env.example)
