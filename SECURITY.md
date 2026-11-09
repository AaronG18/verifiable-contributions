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
- All third-party actions are pinned to a full commit SHA.
- Evidence produced by a contributor is never trusted without independent replay.
