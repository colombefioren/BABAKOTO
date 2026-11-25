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

## Train from scratch and export

Prepare the external [Piper 1.8.0 training environment](https://github.com/OHF-Voice/piper1-gpl/blob/v1.8.0/docs/TRAINING.md)
at commit `639388b6317fc4731e91d53da42aea68fd4166ff`. Use PyTorch 2.8.0 with
the appropriate CUDA build for this Piper release's ONNX exporter. Build Piper's
alignment extension as documented upstream. In that private environment install
this project's `packages/malagasy-text` and `training/tts` packages.

```sh
mkdir -p outputs
python -m babakoto_training_tts.train \
  --prepared data/tts/prepared --out outputs/babakoto-tts --epochs 100
```

Choose the epoch count after checking the recording corpus and available GPU.
Alternatively, import and call `babakoto_training_tts.train.train` in a private
Python GPU notebook with the training environment already installed. Training
and export run in the kernel process without a service or port. Use the default
GPU accelerator for actual voice training.

The command checks the corpus receipt, starts with no pretrained weights, and
disables Piper's optional perceptual model and audio logging. It writes the
ONNX graph, voice configuration and provenance together under `voice/`.
Training artifacts stay under the private run directory. Use a new directory for
each run. Have a native speaker evaluate a separate prompt set before deployment.
