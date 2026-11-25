# Local Malagasy voice training

Use studio recordings from one speaker with an exact transcript per recording. Verify
a signed agreement that explicitly authorizes creating and using a synthetic voice.
Use recordings with rights appropriate for the intended deployment. Keep the signed
agreement, original and prepared audio, transcripts, checkpoints and exports outside
Git. The corpus preparation command checks that the agreement file exists. The
operator verifies its contents and the speaker's identity.

## Prepare a corpus

Record one mono PCM16 WAV at 24 kHz per utterance. Create a private JSON array where
each object has an `audio` path relative to the recordings directory and the exact
`text` transcript. Use a new output directory under the ignored `data/` tree.

```sh
uv run python -m babakoto_training_tts.corpus \
  --root data/tts/recordings \
  --clips data/tts/clips.json \
  --signed-consent /private/path/speaker-agreement.pdf \
  --out data/tts/prepared
```

The command verifies audio, rejects duplicate clips and applies the same Malagasy text
normalizer used by the service. It writes Piper-compatible metadata, a grapheme map,
prepared recordings and an integrity receipt. The receipt contains a hash of the
agreement, while the agreement stays in its original private storage.
