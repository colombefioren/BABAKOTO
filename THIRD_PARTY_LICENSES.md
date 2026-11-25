# Third-party models, datasets and frameworks

Babakoto's code is Apache-2.0. The assets below are **not** distributed with this repo;
each keeps its own license. Status values:

- **REPORTED**: license taken from the upstream card on 2026-11-23, not yet re-checked by a
  maintainer against the exact revision we pin. Re-verify before any release.
- **UNVERIFIED**: license unknown, unclear or contradictory. Do not use in a released model.
- **NC**: non-commercial. Local development and research only, behind
  `ALLOW_NON_COMMERCIAL_ASSETS=true`, never a production default, never redistributed.

## Models

| Asset                                                   | Use                                | License                                                                                                                           | Status              | Link                                                             |
| ------------------------------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------- | ---------------------------------------------------------------- |
| Sunbird/SunflowerASR-51-african-languages               | Default STT                        | Apache-2.0                                                                                                                        | REPORTED            | https://huggingface.co/Sunbird/SunflowerASR-51-african-languages |
| Meta Omnilingual ASR (facebookresearch/omnilingual-asr) | Second opinion for pseudo-labeling | to confirm                                                                                                                        | UNVERIFIED          | https://github.com/facebookresearch/omnilingual-asr              |
| openai/whisper-large-v3-turbo                           | Base for our ASR fine-tune         | MIT per the model card                                                                                                            | REPORTED            | https://huggingface.co/openai/whisper-large-v3-turbo             |
| k2-fsa/OmniVoice                                        | Self-hosted TTS                    | Code Apache-2.0. Weights CC-BY-NC per the model card (training-data constraints, e.g. Emilia). Authors not yet asked to relicense | NC                  | https://huggingface.co/k2-fsa/OmniVoice                          |
| facebook/mms-tts-mlg                                    | Dev-only TTS                       | CC-BY-NC-4.0                                                                                                                      | NC                  | https://huggingface.co/facebook/mms-tts-mlg                      |
| mimba/* Malagasy TTS models                             | Reference only                     | Non-commercial, synthetic                                                                                                         | NC, do not train on | https://huggingface.co/mimba                                     |

## Datasets

| Asset                                | Use                           | License                       | Status              | Link                                                                 |
| ------------------------------------ | ----------------------------- | ----------------------------- | ------------------- | -------------------------------------------------------------------- |
| google/WaxalNLP (`mlg_asr`)          | ASR training and eval         | to confirm for this subset    | UNVERIFIED          | https://huggingface.co/datasets/google/WaxalNLP                      |
| malagasy-asr/malagasy-asr-100h-split | ASR training and eval         | not yet verified              | UNVERIFIED          | https://huggingface.co/datasets/malagasy-asr/malagasy-asr-100h-split |
| DigitalUmuganda/AfriVoice (Malagasy) | ASR training, pseudo-labeling | CC-BY-4.0, gated              | REPORTED            | https://huggingface.co/datasets/DigitalUmuganda/AfriVoice            |
| VoxMg                                | ASR training                  | release and license to locate | UNVERIFIED          | AfricaNLP 2023                                                       |
| mimba/plt-tts-dataset                | Reference only                | Non-commercial, synthetic     | NC, do not train on | https://huggingface.co/datasets/mimba/plt-tts-dataset                |

Contamination note: SunflowerASR was trained on WAXAL Malagasy, so WAXAL test data must not be
used to evaluate it. WAXAL and `malagasy-asr-100h-split` overlap and must be deduplicated.

## Frameworks and services

| Asset                     | Use                                | License                                                  | Status     |
| ------------------------- | ---------------------------------- | -------------------------------------------------------- | ---------- |
| LiveKit server and Agents | Real-time transport, agent runtime | Apache-2.0                                               | REPORTED   |
| Silero VAD                | Voice activity detection           | MIT                                                      | REPORTED   |
| Gladia API                | Optional cloud STT                 | Commercial terms; read before using outputs for training | UNVERIFIED |

Python and JavaScript package dependencies are tracked by `uv.lock` and `pnpm-lock.yaml`.

## Local TTS runtime

ONNX Runtime is used to serve operator-trained VITS voices on the CPU (MIT, REPORTED).
[Published package metadata](https://pypi.org/project/onnxruntime/1.32.0/)

## Local TTS training tool

Piper 1.8.0 is a separately installed GPL-3.0 training tool (REPORTED). Babakoto
does not ship Piper code, pretrained voices, or corpora. The trained voice's
permissions depend on the speaker agreement and applicable training data rights.
Review those permissions before any use outside the agreement.
[Upstream training project](https://github.com/OHF-Voice/piper1-gpl/tree/v1.8.0)
