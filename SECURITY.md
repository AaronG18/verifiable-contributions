# Security Policy

## Reporting a vulnerability

Please report security issues through GitHub's private vulnerability reporting
(https://github.com/AaronG18/verifiable-contributions/security/advisories/new).
Do not open a public issue for a vulnerability.

You can expect an acknowledgement within 7 days. If there is no response in that
time, comment on any open pull request to draw attention to the report.

## Scope

This project executes untrusted code by design: it verifies pull requests from
third parties. Reports about sandbox escapes, arbitrary code execution outside the
verification boundary, secret leakage, or evidence forgery are in scope and are
the highest priority.

## Design constraints

- Verification runs with read-only repository permissions and no secrets.
- Untrusted contributor code is never run in a workflow that holds a write token.
- No workflow uses `pull_request_target` to check out and execute PR head code.
- Third-party actions should be pinned to a full commit SHA in production. The
  in-repo workflows currently use major-version tags for the MVP; see the note
  in `docs/threat-model.md` about supply-chain risk before deploying this.
- Evidence produced by a contributor is never trusted without independent replay.

## Known limitations

Verification runs the repository's own test command, so it executes untrusted
code by design. It uses a read-only token, no secrets, no persistent credentials
and a timeout, but it does **not** provide a container sandbox or network
isolation. For untrusted contributions use a disposable runner with restricted
egress. A receipt is a structured record, not a signature; see
`docs/threat-model.md` for the full list of what it does and does not prove.
