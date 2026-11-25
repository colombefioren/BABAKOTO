# Configure an agent

1. Open **Agent configurations**, select **New agent** and set a name and system prompt.
2. Enter an optional greeting, then save.
3. Select **Manage knowledge** and add plain-text documents relevant to the
   agent. Give each document a descriptive title.
4. Select **Open in playground** from the saved agent and start a new call.

The worker loads the saved prompt and greeting when the caller joins. It searches
the selected agent's documents after a completed utterance. A read-only tool
lets the model refine the lookup where the provider supports tool calls.
Retrieved excerpts may be sent to the configured LLM. Only add documents
you are authorized to use with that provider.

## Serve a local voice

Use an export from the private
[consented voice training pipeline](https://github.com/colombefioren/BABAKOTO/blob/main/training/tts/README.md).
Set `BABAKOTO_TTS_MODEL_PATH` to the absolute path of its `voice/` directory.
After verifying the signed agreement covers the deployment, set
`BABAKOTO_TTS_CONSENT_CONFIRMED=true`. Choose `TTS_CPU_ENGINE=babakoto-tts` for
CPU or `TTS_ENGINE=babakoto-tts` for GPU. The local engine uses the CPU.
[Voice artifact and mount requirements](https://github.com/colombefioren/BABAKOTO/blob/main/services/tts/README.md)

OmniVoice and MMS are non-commercial research options. They require explicit
opt-in and a pinned revision. OmniVoice also requires the speaker's signed
voice-cloning consent before use.
[Third-party licenses](https://github.com/colombefioren/BABAKOTO/blob/main/THIRD_PARTY_LICENSES.md)

## Operate a private stack

- The bundled host ports bind to loopback. Keep the speech services, API and
  PostgreSQL on their private networks.
- Keep local credentials, recordings and consent documents out of Git. Back up
  the PostgreSQL volume privately if you need to retain agent settings and
  knowledge documents.
- The bundled stack keeps call audio and captions in memory during a call. Cloud
  providers can retain data under their own account settings. Review those
  settings and disclose the applicable processing before recording or testing.
- The token limit and concurrent-room cap are designed for one issuer on a
  dedicated local LiveKit instance. An internet deployment needs TLS,
  application authentication and edge rate limiting. Multi-instance admission
  needs shared limits. [Deployment decisions](https://github.com/colombefioren/BABAKOTO/blob/main/docs/DECISIONS.md)

## Verify a deployment

Run `just check` for local tests. Use the evaluation scripts to measure latency
and compare ASR WER on approved recordings. The scripted latency test covers
the pipeline and has a separate live browser acceptance check.
[Evaluation commands](https://github.com/colombefioren/BABAKOTO/blob/main/eval/README.md)
