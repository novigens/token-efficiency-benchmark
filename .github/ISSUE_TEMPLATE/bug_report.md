---
name: Bug report
about: A reproducible problem in the generator, harness, or scorer
labels: bug
---

## What happened

A clear statement of the bug. If it is a *generator bug* (a task that should not have been generated, or a malformed merged prompt), tag this issue `generator-bug` as well; those are highest priority because they affect benchmark correctness.

## How to reproduce

```bash
# minimal command(s) that reproduce
teb generate --template ... --seed ... --out ...
```

- Generator version (`teb --version`):
- Seed:
- Python version:
- OS:

## Expected vs. actual

- Expected:
- Actual:

## Attachments

For evaluation bugs, please attach the JSONL result file for the affected tasks. For generator bugs, the offending task JSONL is sufficient.
