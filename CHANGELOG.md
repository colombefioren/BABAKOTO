# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## 0.1.0 (2026-11-28)


### Features

* add a dashboard editor for saved agent configurations ([1f0b4d0](https://github.com/colombefioren/BABAKOTO/commit/1f0b4d06edf2deecde378d061e5e29c866f9ecf5))
* cap concurrent playground room admissions ([f64d555](https://github.com/colombefioren/BABAKOTO/commit/f64d5550611a3da57e8d8ae1c9dedd55926737c4))
* edit agent knowledge in the dashboard ([73e22dd](https://github.com/colombefioren/BABAKOTO/commit/73e22ddf5b8c4722dd97aad0aaddd459f710dbf5))
* enable local Malagasy ASR training ([0b92997](https://github.com/colombefioren/BABAKOTO/commit/0b929975657a7b6cd2aac2b7321ed471de38d215))
* expose a scoped knowledge search tool to saved agents ([95160dc](https://github.com/colombefioren/BABAKOTO/commit/95160dc57822164ffc7785ddf159ded7f99261cb))
* implement latency benchmark and Molab GPU notebook ([8339164](https://github.com/colombefioren/BABAKOTO/commit/83391640213dc8f471e1fc8257fa5a44d99d438c))
* implement LiveKit agent worker with provider abstraction and barge-in settings ([4417ef9](https://github.com/colombefioren/BABAKOTO/commit/4417ef9d0a0fe9018609f188b912bb73d3e169fb))
* implement Malagasy text normalizer with 100+ test cases ([39ab874](https://github.com/colombefioren/BABAKOTO/commit/39ab87458387aa69a2689740514bc04cc5f96571))
* implement Next.js playground with live captions and per-reply latency ([1741e77](https://github.com/colombefioren/BABAKOTO/commit/1741e775ba7f238e6649c976a921aa1f61acdcec))
* implement STT service wrapping SunflowerASR ([9f4a70d](https://github.com/colombefioren/BABAKOTO/commit/9f4a70d39f2bf094412d1a500faad31761f747df))
* implement TTS service with sentence-by-sentence streaming ([d2b7afb](https://github.com/colombefioren/BABAKOTO/commit/d2b7afb0e3e8a78a8f45baacc499a3ba6a2755f5))
* package the Milestone 1 voice playground ([2741ca6](https://github.com/colombefioren/BABAKOTO/commit/2741ca624206a15c692ffee9a0abc1c6e05e92b7))
* persist agent configurations in PostgreSQL ([a6c8d42](https://github.com/colombefioren/BABAKOTO/commit/a6c8d4275a3d70f95d78113c3173a076b92ad128))
* prepare consented recordings for local voice training ([13392d4](https://github.com/colombefioren/BABAKOTO/commit/13392d4b131d30cdc3347bc2a5c8691920d93301))
* require operator authentication for the playground ([38764ca](https://github.com/colombefioren/BABAKOTO/commit/38764cadb3da83ddfd9f5cd2d7403843f92dfb1f))
* retrieve agent knowledge for voice replies ([03885ae](https://github.com/colombefioren/BABAKOTO/commit/03885aec8aa10006dcd2df239642bdf78eefa3cd))
* serve trained local voices through the TTS service ([f9c60c2](https://github.com/colombefioren/BABAKOTO/commit/f9c60c299eb658a48718b9823fbabd57350f20aa))
* store agent knowledge documents in PostgreSQL ([febd64c](https://github.com/colombefioren/BABAKOTO/commit/febd64ce5707e4a65ac8bdff02e12d1d5f9dbaf5))
* train a local VITS voice from consented audio ([031bd05](https://github.com/colombefioren/BABAKOTO/commit/031bd0526ac08fd7810714ad93bf90d0e7c11bba))
* use saved agent configurations in voice calls ([1c569fe](https://github.com/colombefioren/BABAKOTO/commit/1c569fedd984d91f1a6c71b4ad60d7ca8fca7878))


### Bug Fixes

* attribute playground captions to the speaker ([c6aeaee](https://github.com/colombefioren/BABAKOTO/commit/c6aeaee3c8a9f48fbdedf907f154280e69d7f4b1))
* complete knowledge retrieval before voice generation ([d6f2275](https://github.com/colombefioren/BABAKOTO/commit/d6f227580f507539ca3616b8508a16bfd3c5e003))
* enforce STT upload cap before multipart parsing using a body size middleware ([73089bc](https://github.com/colombefioren/BABAKOTO/commit/73089bc884c2e79a1da3a3d1f33f3e4070705fc8))
* require signed consent before reference voice cloning ([82b1c27](https://github.com/colombefioren/BABAKOTO/commit/82b1c278100ad6c2fc4b6ff5712d748dc1b5cf2e))
* wait for LiveKit worker readiness during startup ([6805be9](https://github.com/colombefioren/BABAKOTO/commit/6805be904b7188c47a378e230571931dc5b8530d))

## [Unreleased]

### Added

- Repository foundations: license, policies, third-party license register, environment
  template.
