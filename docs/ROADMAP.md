# Roadmap

Current release: **2.0.0**. TaskFamily architecture, burn-after-reading runs,
dollar economics, three providers. See `CHANGELOG.md`.

## Next (build order from design_v2.md §9)

1. **First multi-model leaderboard**: 9-model roster across Moonshot, OpenAI,
   Anthropic; standard 4-cell run; published with manifests for replay.
2. **`consistency` family port** (grader already ships). All three core
   families (`arithmetic_chain`, `program_output`, `table_aggregation`) and
   the hybrid recipes (`prog+chain`, `chain+table`, default
   `prog+chain+table`) shipped in 2.0.0.
3. **More hybrid recipes and bridges**: program→table joints, longer
   recipes, per-segment difficulty control.
4. **Statistical protocol automation** (`--target-ci` sampling): generate
   until the confidence interval on efficiency is narrower than a target.
5. **Difficulty evolution loop**: when reference models saturate a region,
   mutate difficulty axes until discrimination returns; restore the parked
   drift-monitor and empirical-calibration instrumentation.

## Later

- Realism anchors (source-benchmark-derived families), LLM-assisted surface
  rendering behind a re-extraction verifier, agentic/tool-use cost accounting,
  validation against measured costs on real enterprise workloads.
