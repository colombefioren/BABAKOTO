# Publish the first source preview

Release Please proposes `v0.1.0` and updates the changelog. The release pull
request is a draft while acceptance is outstanding. After the release pull
request merges, the workflow prepares a draft GitHub prerelease for review.

## Acceptance before publication

- Run the five-turn browser call, latency benchmark and interruption check.
  Record commands, hardware and results in the milestone issue.
  [Live-call acceptance](https://github.com/colombefioren/BABAKOTO/issues/15)
- Compare the trained ASR and the pinned baseline on an independently collected,
  approved held-out corpus. [ASR acceptance](https://github.com/colombefioren/BABAKOTO/issues/33)
- Train with consented voice data and have a native speaker evaluate the local
  voice. Complete the review of product prompts and benchmark utterances.
  [Voice acceptance](https://github.com/colombefioren/BABAKOTO/issues/44)
  · [Native review register](NEEDS_NATIVE_REVIEW.md)
- Verify the applicable third-party license terms against the pinned revisions.
  Preserve the non-commercial opt-in for OmniVoice and MMS.
  [License register](../THIRD_PARTY_LICENSES.md)

## Preflight

1. Confirm the pull request proposes `v0.1.0` and only changes release metadata.
2. Verify the required branch checks and the [operator guide](https://colombefioren.github.io/BABAKOTO/).
3. Review the release notes against [measured results and open limitations](PROGRESS.md).
4. Merge the approved release metadata. Review the draft on GitHub. The preview
   distributes source only. Keep all data, audio, consent documents, credentials
   and weights outside the published release.
