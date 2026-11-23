# Security Policy

## Supported versions

Babakoto is pre-1.0. Only the latest release and `main` receive security fixes.

## Reporting a vulnerability

Do not open a public issue for security problems. Use GitHub's private vulnerability
reporting: open the repository's **Security** tab and choose **Report a vulnerability**.

Include what you found, how to reproduce it, and the impact. We aim to acknowledge reports
within 5 working days and to publish a fix or mitigation within 90 days.

## Scope notes

- Never include real user recordings, transcripts or credentials in a report.
- Secrets must never be committed. Secret scanning and push protection are enabled on this
  repository, and `gitleaks` runs in pre-commit and CI.
- Webhook tools are subject to SSRF protection (private IP ranges blocked), planned for
  Milestone 4.
