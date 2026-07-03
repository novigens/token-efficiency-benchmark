---
name: Design RFC
about: Propose a substantive change to benchmark methodology or settled design properties
labels: rfc
---

## What you propose to change

A precise statement of the proposed change. Cite the section in `docs/design_v2.md` that the change affects.

## Why

What failure mode does this address that the current design does not? Be specific: a "preference" is not sufficient justification for changing a settled property. See `CONTRIBUTING.md` for the list of settled properties.

## What breaks

Which existing tests fail? Which existing replays become incomparable? Does this require a major generator version bump?

## Alternatives considered

What else could solve the same failure mode? Why is this the right one?

## Migration

If accepted, how do existing users move forward? Is there a deprecation window?
