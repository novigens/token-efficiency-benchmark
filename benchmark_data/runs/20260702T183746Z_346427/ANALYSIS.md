# Smoke run analysis: moonshot:kimi-k2.5

Run `20260702T183746Z_346427`, arithmetic_chain v2.0.0, fresh entropy seed
(see `manifest.json`). 23/40 tasks completed; the 17 missing were killed by the
sandbox's 45 s per-call limit, not by the model. **Censoring caveat:** the
killed tasks are the slowest (longest-thinking) ones, so deep-cell efficiency
below is biased optimistic; true waste at depth 10/14 is higher than measured.

## Results (completed subset)

| depth | n | acc | mean out_tok | efficiency | waste × | \$/task |
|---|---|---|---|---|---|---|
| 3 | 9 | 1.000 | 669 | 0.032 | 38.5 | \$0.00205 |
| 6 | 10 | 1.000 | 797 | 0.046 | 23.1 | \$0.00247 |
| 10 | 3 | 1.000 | 984 | 0.052 | 19.1 | \$0.00308 |
| 14 | 1 | 1.000 | 1106 | 0.055 | 17.2 | \$0.00347 |

Aggregate: accuracy 1.000, \$/correct = \$0.00243, mean waste 28.4×, spend \$0.0559.

## Findings

1. **Accuracy does not discriminate** at these depths: 100% everywhere,
   exactly as predicted when we repositioned efficiency as the product.
2. **The waste ratio is the story: 28× mean overspend.** The model emits
   ~670 to 1,100 output tokens for answers whose canonical form is one token.
3. **Waste is worst on the easiest tasks** (38.5× at depth 3 vs 17× at depth
   14): K2.5 carries a ~600-700 token fixed reasoning overhead regardless of
   task size, so proportional waste is highest on trivial work. For the
   token-value-gap narrative this is the headline: enterprises running
   reasoning-class models on shallow tasks pay the largest proportional tax.
4. **Output tokens scale with depth** (669 → 1,106), i.e. thinking spend grows
   with hidden-chain length; the depth axis works as a cost dial even where
   accuracy is flat.
5. Wall-clock latency also scaled with depth (deep tasks routinely exceeded
   40 s), consistent with billed thinking effort.

## Next

- Re-run uncensored on a machine without the 45 s limit (see README/bash line).
- Add a small non-reasoning model for the fixed-overhead comparison.
- Distractor-density effect needs the uncensored run to evaluate.
