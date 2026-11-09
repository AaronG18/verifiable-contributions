# Threat model

This document states what a verification receipt proves, what it does not
prove, and which attacks are in scope. Being explicit about the limits is the
point of the project: a maintainer should never have to guess how much trust
to place in a badge.

## Trust anchor

The receipt is produced by a CI job defined on the repository's default
branch, triggered by `pull_request` with `contents: read`, no secrets, and
`persist-credentials: false`. The maintainer controls that workflow. A
contributor controls the PR's source and test files.

Everything below follows from that split.

## What the receipt does establish

- The two commit SHAs that were compared.
- The exact command that was run, read from the policy on the base commit.
- The digests of every test file that was copied onto the base tree.
- The exit code and output digests of both runs, in the runner's environment.
- That the head's source change was **not** copied onto the base tree.
- Whether the PR touched the verifier or its policy (`UNTRUSTED`).

If `vrc check` passes, the receipt was not edited after generation and its
verdict is consistent with the recorded exit codes.

## What it does not establish

- **Correctness.** A test can fail on base and pass on head while asserting the
  wrong behaviour. This tool measures whether a test discriminates between two
  trees, not whether the change is right.
- **Authorship or understanding.** It does not detect AI-written code and does
  not record anything about a contributor. That is intentional: authorship
  detection is unreliable and punishes people who did nothing wrong.
- **Provenance and licensing.** It says nothing about where generated code came
  from or whether it can be redistributed.
- **Security of the change.** Tests are executed, not sandboxed against a
  malicious test suite. See the isolation section.
- **Cryptographic non-repudiation.** The digest is a checksum, not a signature.
  Anyone who can write the artifact can recompute it. Stronger guarantees need
  signed attestations (SLSA/in-toto/Sigstore), which are not in this MVP.

## Attacks and current mitigations

| Attack | Mitigation | Residual risk |
| --- | --- | --- |
| Paste a fake "tests pass" log in the PR body | CI generates the receipt; contributor-supplied logs are ignored | None for the receipt itself |
| Weaken the command or test paths in the same PR | Policy is read from the base commit; protected paths force `UNTRUSTED` | A previously merged malicious policy is trusted by definition; that is a review failure on the maintainer side |
| Write a vacuous test that always passes | Base run must fail, otherwise `NEEDS_EVIDENCE` | A test that fails on base for an unrelated reason still counts; see below |
| Make the base run fail for an unrelated reason (import error, missing dependency) | `NEEDS_RERUN` only triggers when the head fails; a base failure with head passing is `VERIFIED` | **Open problem.** The MVP does not distinguish an assertion failure from an import error. Reviewers should read the base stderr excerpt. Classifying failure reasons is on the roadmap |
| Game the test file overlay by placing source code under a test path | Anything under `test_paths` is copied, so this can carry the fix onto the base tree | Reviewers see the copied file list; keep `test_paths` narrow. Detecting source/test overlap is on the roadmap |
| Exfiltrate secrets from a test | `pull_request` has no secrets; env vars matching `SECRET`, `TOKEN`, `PASSWORD`, `CREDENTIAL`, `API_KEY`, `PRIVATE_KEY` are stripped; read-only token; `persist-credentials: false` | Network egress is **not** restricted. A test can still make outbound requests. Use a runner with restricted egress for untrusted contributions |
| Malicious `git archive` member (path traversal, symlink, device) | Members are validated before extraction; absolute paths, `..`, links, devices and FIFOs are rejected | Git's own archive output is trusted |
| Alter the receipt after generation | `vrc check` recomputes the digest and re-derives the verdict | No signature: an attacker with artifact write access can recompute both |
| Tamper with the verifier itself | `protected_paths` triggers `UNTRUSTED`; merging a change to the verifier or its workflow still requires the PR approval recorded on `main` | The in-repo `uses: ./` action is loaded from the **PR head**, not the default branch, so a PR can change the action code that runs. This is contained by `pull_request` (read-only token, no secrets, no persistent credentials) and by the approval gate before merge, but it is not a sandbox. Note that the owner's agent may submit that approval for the owner's own PRs; external PRs need a human review. A compromised maintainer account defeats any in-repo control |

## Isolation boundary

The verifier runs the repository's own test command. That is arbitrary code
execution by design. It runs with a read-only token, no secrets, no persistent
credentials, and a timeout, but **not** inside a container sandbox or with
network isolation. For projects accepting untrusted contributions, run this in
a disposable runner with restricted network egress, and never under
`pull_request_target`.

## Reporting a problem

Use private vulnerability reporting as described in [SECURITY.md](../SECURITY.md).
Reports about evidence forgery, sandbox escapes, or secret leakage are the
highest priority.
