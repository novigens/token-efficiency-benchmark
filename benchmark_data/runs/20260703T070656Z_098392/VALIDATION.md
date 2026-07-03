# Pre-flight validation (single task, all candidate configs)

Task: the run's task ending `636affda54a4` (hybrid prog+chain+table, depth 3,
correct answer **54**). Each config was exercised once via raw curl before the
run, July 3 2026. Full JSON responses preserved in the session log.

| Config | Output tokens | Hidden thinking | Answer | Verdict |
|---|---|---|---|---|
| moonshot:kimi-k2.5 (default, 4096 cap) | 4,096 (truncated) | all | none emitted | overthinking: correct answer visible in reasoning trace, never stated |
| moonshot:kimi-k2.5 **#thinking=off** | 687 | 0 | **54 ✓** | selected |
| anthropic:claude-sonnet-5 (default) | 693 | 300 | **54 ✓** | selected |
| openai:gpt-5.4 (default) | 4 | 0 | 105 ✗ | underthinking: instant confident wrong answer |
| openai:gpt-5.4 **#effort=medium** | 418 | 408 | **54 ✓** | selected |

## Selection note (methodological honesty)

The three selected rows are the configurations that answered the validation
task correctly. Exclusion after peeking at one task is selection-on-outcome;
this run is therefore framed as a **cost-comparison shortlist among viable
configurations**, not a neutral full-roster leaderboard. The excluded configs'
single-task behavior is documented above and their full-roster evaluation
remains replayable from this run's tasks.jsonl at any time.

## Incidental findings worth keeping

- All three providers bill hidden thinking as output tokens; only Moonshot
  returns the thinking text; Anthropic attests it (signed, redacted, counted);
  OpenAI returns counts only.
- Vendor knobs are opposite-handed: OpenAI reasoning is opt-in
  (`reasoning_effort`), Moonshot is opt-out (`thinking.type=disabled`), and the
  dialects are mutually rejected across vendors.
- On the validation task, K2.5-instant produced the cheapest correct answer
  (~\$0.0022) using nearly the same token budget as Sonnet 5 (687 vs 693) at a
  third of the unit price, while K2.5's own default thinking mode spent 6x
  more tokens and produced nothing.


## Batch 2 note (2026-07-03, post-publication)

The nine additional configs (nanos, effort=low, haiku, opus, gpt-5.5, fable-5, k2.6 both modes)
ran without per-config pre-flight probes. Post-hoc audit of all 260 rows is in ANALYSIS.md;
notable findings there: fable-5 returned stop_reason=refusal on 5/20 arithmetic tasks,
k2.6 default thinking died once at the 16,384 output cap, and the most-missed task
(..2c6004c33dde) was re-derived by hand to confirm generator integrity (answer 6911).
