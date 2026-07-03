---
name: New source-benchmark adapter
about: Propose adding a new source benchmark to the generator
labels: adapter
---

## Source benchmark

- Name:
- Upstream URL:
- Version / SHA you intend to pin:
- License (must be compatible with re-distribution of items, or items must be referenced by ID only):

## Fit assessment

Following the §10.1 / §5.1 criteria, please describe:

- **Answer type**: integer, real, multiple-choice index, code object, structured tuple, ...
- **Verification method**: exact match, numerical tolerance (state tolerance), execution against unit tests, ...
- **Subset of items admitted**: which items pass the "uniquely-determined answer, discretizable, can serve as a parameter" criteria. Roughly what fraction of the source benchmark does this leave?
- **Parameter templates**: what kind of downstream problems can this adapter's answers feed into?

## Why this benchmark is worth adding

What capabilities, domains, or failure modes does this adapter expand the generator's reach over? What composition templates does it unlock that current adapters do not?

## Risks

Known errata, ambiguous items, items with multiple defensible answers, contamination concerns (heavily-discussed benchmark items that may be memorized), licensing constraints.
