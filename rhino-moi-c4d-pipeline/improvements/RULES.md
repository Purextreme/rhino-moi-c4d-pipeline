# Rhino MoI C4D Pipeline Improvement Queue Rules

This directory is a review queue for reusable experience observed during real Rhino to MoI to C4D runs. Each file under `pending/` is a candidate, not an established Skill rule.

## Recording workflow

- Record only behavior observed in a real run with concrete evidence such as an error, warning, command, probe, or generated artifact.
- Record only after the main task is safe and verified. Logging must not interrupt recovery or delay delivery.
- Before recording, read only this file. Do not list, search, or read existing files under `pending/`; duplicate detection belongs to maintainer review.
- Create exactly one new Markdown file per candidate. Do not append to or rewrite another entry.
- Name files `YYYY-MM-DDTHH-mm-ss-short-title.md`, using a concise lowercase ASCII slug. Add a numeric suffix only when that exact path already exists.
- Set `Status` to `pending review`.
- Exclude user secrets, private model contents, generated model metadata, absolute machine paths, process IDs, and other unnecessary machine identifiers.
- Do not promote a candidate into `SKILL.md`, references, or scripts without maintainer review.

## Entry template

```markdown
# Short title

- Status: pending review
- Date: YYYY-MM-DD
- Context: The operation and environment that exposed the issue.
- Observation: The exact behavior, error, or warning.
- Evidence: The relevant command, probe, or reproducible condition without private data.
- Workaround: What safely unblocked the task.
- Candidate destination: The smallest likely `SKILL.md`, reference, or script location.
- Review notes:
```

## Maintainer review

Only when review or absorption is explicitly requested, inspect pending candidates, consolidate duplicates, validate their evidence, and accept or reject each item. Promote accepted knowledge to the smallest canonical destination, then remove the reviewed candidate. Never treat an unreviewed entry as established guidance.
