# Babakoto

Babakoto is an Apache-2.0 project for self-hosted Malagasy voice agents. A browser
call reaches the LiveKit worker over WebRTC. The worker detects speech with
Silero VAD, transcribes it, sends the turn to the configured language model and
plays the synthesized reply.

Babakoto is in preview. The playground supports captions, interruption and
per-reply latency display. Saved agents can use a custom prompt, greeting and
private knowledge documents. A locally trained voice can be mounted into the
speech service. Approved corpora, live-call performance and native voice quality
are still being evaluated.

- [Start the local playground](quickstart.md)
- [Configure an agent and operate the stack](operator.md)
- [Lire la documentation en français](fr/index.md)
- [Check milestone status](https://github.com/colombefioren/BABAKOTO/blob/main/docs/PROGRESS.md)
