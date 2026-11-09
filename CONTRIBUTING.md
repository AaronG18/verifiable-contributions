# Contributing

Every change to `main` goes through a pull request. Direct pushes are blocked,
force pushes and branch deletion are blocked, and the `verify` status check must
pass. Merges are squash-only. There are no bypass actors.

The code owner's own changes (including changes made by an agent acting for the
owner) may be approved and merged by that agent without a separate human review.
The PR is still required, and the review and CI results are still recorded. Work
done this way uses a `work/` branch and is opened by the `open-pr` workflow, so
the PR author is `github-actions[bot]` and an approval can be submitted.

Pull requests from external contributors are different: they require a human
review from the code owner. An agent acting for the owner must not approve or
merge someone else's PR. This is the project's own first line of defence against
unreviewed machine-generated changes, and it is the same standard this tool asks
other projects to adopt.

## Before opening a pull request

1. Open or find an issue describing the problem first. Explain why the change
   should exist, not only what it does.
2. Keep the diff small and scoped to that issue.
3. Add a regression test that fails without your change and passes with it.
4. Run the checks locally and paste the real command output in the PR body. If
   the full suite cannot run in your environment, say so plainly instead of
   claiming a run you did not do.
5. Disclose AI assistance in one line. AI-assisted work is welcome; the human
   submitting it is accountable for understanding and maintaining it.

## PR description

Include: the root cause, the exact test added and what it asserts, verifiable
evidence (test output or CI result), and who you are asking for review. Plain
prose is preferred over long generated checklists.

## Verification standard

This project exists because maintainers cannot cheaply verify machine-generated
contributions. We hold our own PRs to the same standard we ask of others: an
independent party must be able to reproduce the claim from the PR alone.
