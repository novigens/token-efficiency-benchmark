# Token Efficiency Benchmark: v2 Architecture

**Status:** the current architecture (2.0.0). This document is self-contained; together
with `docs/examples_v2.md` it is the authoritative specification.

## 1. Northstar

Measure the **cost of a correct outcome** on any model, in a way that no model can game
by memorization, verbosity, or confident hallucination.

The market context: enterprises pay per token while value arrives per correct outcome
(the "token backlash").
This benchmark is the measurement instrument for that gap. Headline outputs:

- `efficiency = V* / cost-weighted tokens`, conditional on a correct terminal answer
- `$ per correct outcome = total spend ÷ correct answers` under any provider price sheet
- difficulty-stratified degradation curves with variance

Five load-bearing requirements:

1. **Ground truth by construction or execution.** Never a solver, never an LLM judge,
   never a heuristic. If truth cannot be computed exactly, the task is not generated.
2. **Burn-after-reading protocol.** Tasks are generated fresh per run from seeds drawn at
   evaluation time. After scoring, generator version + seeds + full replays are published;
   those instances are burned, the next run draws new ones.
3. **Merged single-prompt presentation.** The decomposition is hidden; recovering it is
   the model's job.
4. **Cost-weighted scoring.** `cost = w_in·input + w_out·output`, default (1, 4), raw
   counts always published for re-weighting, plus a pricing layer
   mapping counts to dollars per provider.
5. **Full replay.** Every result reproducible from (generator_version, family, seed).

## 2. The core asymmetry (why this works)

The generator holds the witness: the composition graph and every intermediate value.
Forward generation is O(depth) substitution. The model must reconstruct enough of the
hidden witness from merged prose to emit the terminal answer. Verification is exact
match against the constructed truth. **Cheap forward, expensive backward, trivially
checkable**: the generator-verifier gap is the engine of contamination resistance and
of the metric itself.

Precision about where the backward hardness lives, per family class:

| Family class | Worst-case complexity of the backward task | Where the difficulty actually is |
|---|---|---|
| Narrative arithmetic chains | P (linear, once decomposed) | Decomposition discovery: recovering the hidden dependency DAG from prose under distractors |
| Program-output prediction | P-complete | No shortcut around simulation; required internal work scales directly with program size |
| Logic grids / CSP | NP-complete; uniqueness promise does **not** restore tractability (Valiant-Vazirani) | Search; clue set is generated constructively so uniqueness is guaranteed without solving |
| Adversarial / planning (future) | PSPACE-complete | Lookahead under opposition |

Two disciplines follow:

- **No worst-case bragging.** Random instances of hard families are usually easy.
  The defensible claim is: the family is worst-case hard and instance difficulty is
  tuned *empirically* by the evolution loop (§5). Asymptotics set the ceiling;
  calibration finds the frontier.
- **Uniqueness is a grading property, not a difficulty property.** Forward construction
  fixes every value; the renderer's single formal obligation is that the prose admits
  exactly that reading. Uniqueness keeps scoring sound; it does not make search easy.

The economic reading: efficiency = V*/cost measures how much of the backward search the
model externalizes into paid tokens. The complexity asymmetry and the token-value gap
are the same phenomenon, viewed from theory and from economics.

## 3. Minimal architecture

```
src/token_efficiency_benchmark/
  types.py                 # CompositeTask, TaskResult (generalize answer types)
  families/
    base.py                # TaskFamily interface + shared validity checks
    arithmetic_chain.py    # family 1 (shipping; Composable)
    program_output.py      # family 2 (shipping; execution-based truth; Composable)
    hybrid.py              # cross-family composer (default family; 3 recipes)
    table_aggregation.py   # family 3 (shipping; computed-statistic; Composable)
    consistency.py         # family 4 (self-consistency probe; grader ships today)
  evaluation/
    harness.py             # provider-reported token counts for live models
    scoring.py             # + pricing layer ($/correct)
    tokenization.py
    models.py              # fixtures; live_models.py for API clients
  serialization.py         # + round-trip validation on read
  cli.py                   # run | generate | evaluate | score | compare
```

### 3.1 The TaskFamily interface

One abstraction owns generation end to end:

```python
class TaskFamily(Protocol):
    name: str
    version: str

    def generate(self, seed: int, difficulty: DifficultyParams) -> CompositeTask:
        """Deterministic in (version, seed, difficulty).

        Must produce ground truth by construction or execution: the family
        owns its truth computation and its surface rendering. Must raise
        GenerationRejected (never emit) if any validity obligation fails.
        """

    def difficulty_axes(self) -> dict[str, Axis]:
        """The dials the evolution loop may mutate (depth, width, distractors,
        lexicon breadth, value magnitude, ...)."""
```

Validity obligations enforced in `base.py` for every family (reduced to what
generation can guarantee): terminal answer absent from prompt surface; no decomposition
markers; canonical minimal answer form exists; rendering is seed-deterministic.

Design consequences:

- Truth is computed *inside* the family (executed program, computed statistic, forward
  substitution over compute functions). Approximate or heuristic ground truth is
  structurally impossible: there is no shared merging layer to smuggle it in through.
- Rendering is family-owned **grammar-based surface realization**: seedable draws over
  per-family lexicon and paraphrase banks. Deterministic and auditable, with wide surface
  variety to shrink the "detectably synthetic" anchoring surface. LLM-assisted rendering may land later as a *versioned,
  optional* stage behind a re-extraction verifier; it is not in the minimal core.
- No cross-module private imports; no regex substitution into foreign prose.

### 3.2 Roads deliberately not taken

- **Source-benchmark adapters as the spine.** Composing items from public benchmarks
  (GSM8K, HotpotQA, ...) imports their contamination and their free-prose merging
  problem. Executable families dominate on every northstar axis; source-derived
  "realism anchor" families may return later as one family type among many.
- **Solver- or CAS-backed ground truth.** If truth must be searched for, it can be
  wrong. Families only emit tasks whose truth they constructed or executed.
- **LLM-as-judge scoring.** Reintroduces the faithfulness and gameability problems the
  design exists to remove. Grading is exact match or deterministic recomputation only.
- **LLM-driven prompt rendering (for now).** Nondeterministic generation breaks replay;
  may land later as a versioned optional stage behind a re-extraction verifier.

## 4. Launch families

Worked end-to-end examples with concrete values and named test obligations:
`docs/examples_v2.md` (normative: an implementation that
disagrees with those examples contains a bug).

1. **`arithmetic_chain`** (shipping): truth by forward substitution through compute
   functions only. Axes: depth, value ranges, template mix, scenario lexicon,
   distractor quantities.
2. **`program_output`** (shipping): sample a small program from a restricted AST grammar
   (assignments, integer arithmetic, bounded loops, conditionals, string ops); render as
   code or as prose procedure; ask for the printed output. Truth by sandboxed execution
   with step budget; instances exceeding the budget are rejected, making termination a
   generation-time guarantee. Axes: AST depth, variable count, loop nesting, aliasing,
   dead code as distractors.
3. **`table_aggregation`** (shipping): generate a synthetic dataset, narrate it as prose, ask for
   a derived statistic (group-wise max of sums, filtered means). Truth by computing the
   statistic. The enterprise-shaped family: extract → structure → aggregate is the
   document-workflow failure mode buyers recognize. Axes: rows, groups, filter clauses,
   narrative interleaving, unit conversions.
4. **`consistency`**: the grader recomputes the consistency rule on the model's own
   emitted values; there is no fixed answer to memorize even in principle. Unanchorable
   by definition; calibration probe for confabulation. The grader ships in
   `evaluation/consistency_scoring.py`; the generating family is a planned port.

### 4.1 Hybrid compositions (cross-family)

A hybrid task chains **segments from different families**: an executed program's
printed value becomes the opening quantity of a narrative chain; the chain's result
becomes a missing cell in a narrated table. Hybrids are a generation-side concept
only (one merged prompt, one terminal answer, unchanged scoring), which is exactly
why they are cheap to add and expensive to game.

Contract (implemented by families that opt in):

```python
class Composable(Protocol):
    def generate_segment(
        self, seed: int, difficulty: DifficultyParams, upstream: int | None
    ) -> Segment:
        """Statement-form prose (no question), computed terminal value,
        declared output type. Truth is computed by the segment's own family
        given the injected upstream: construction/execution end to end."""
```

A generic `HybridComposer` chains segments per a **recipe** (an ordered list of
family names plus per-segment difficulty), renders typed **bridge phrases** per
(source, target) pair that reference the upstream value without stating it, and
renders only the final segment in question form. Validity: every segment terminal
and intermediate is hidden; a type mismatch at any joint raises
`GenerationRejected` (no implicit coercion). The recipe is recorded in the task's
parameters and difficulty bucket, so hybrid cells stratify like any other.

2.0.0 recipes: ``prog+chain``, ``chain+table``, and the default
``prog+chain+table``, the full gauntlet, one value carried code → narrative →
table. Hybrid is the benchmark's **default family**: the leaderboard runs it
unless a single-family cell is requested. Worked examples: §G and §H.

Why it matters: cross-family handoffs test carrying a value across
*representational* shifts (code → prose → table), the capability
single-family tasks cannot isolate, and the composition space becomes the
product of family spaces, so anchoring difficulty compounds with every family
added. Worked example: `docs/examples_v2.md` §G.

## 5. Evolution loop (design now, build after first real runs)

```
generate (fresh seeds) → evaluate (real models) → score
        ↑                                            |
   mutate difficulty axes of saturated regions  ←────┘
   (accuracy ≈ 1.0, tight variance ⇒ push axes; version-bump family)
```

- Every mutation is a family version bump; results are comparable only within
  (family version, difficulty bucket); scores are never compared across family versions.
- Distribution-drift monitoring and empirical difficulty calibration return as the
  loop's instrumentation.
- Anti-anchoring argument, stated once: a family is a parameterized distribution;
  memorizing any finite sample confers ~nothing; the only way to score is to carry the
  capability. Distillation-narrow models reveal themselves as sharp degradation along
  mutated axes.

## 6. Metric layer additions

Unchanged: efficiency, EVR, configurable weights, bytes-per-correct reporting, raw-count
publication. Added:

- **Pricing tables** (versioned JSON: provider, model, \$/Mtok in, \$/Mtok out) applied at
  scoring time: `teb score --pricing prices.json` emits **\$ per correct outcome** =
  total dollar spend ÷ number correct. Wrong answers inflate the denominator naturally:
  no conditioning, no partial credit. This is the buyer-facing headline number.
- **Provider-reported token counts** for live models (billing truth), local tokenizer
  only as fixture fallback.
- **Waste ratio** = (actual cost − V*) / V*, the per-task overspend factor; the
  aggregate version is the "token-value gap" figure for reporting.

## 7. Statistical protocol

Per (model, family version, difficulty bucket): sample fresh tasks until the 95% CI on
mean efficiency is narrower than a target (default 0.02), or a sample cap is hit
(a planned `--target-ci` flag). Report accuracy,
efficiency, \$/correct, waste ratio, variance, and n. Never rank models within CI overlap.

## 8. Scope honesty

Procedural families are verifiable but synthetic. Evolution solves contamination, not
ecological validity: the claim "predicts your document-workflow cost" requires validating
family 3-style tasks against real workloads, and the unverifiable slice (judgment,
writing quality) remains out of scope. The benchmark measures the token-value gap on the
verifiable multi-step slice; it does not measure everything a buyer cares about.

## 9. Build order

1. `families/base.py` + `arithmetic_chain` (done; tests from `examples_v2.md` §A)
2. Pricing layer + provider token counts + waste ratio (done; §E obligations)
3. `program_output` family (done; §B): execution-based truth, Composable from day one
4. `HybridFamily` + `arithmetic_chain` Composable retrofit (done; §4.1, examples §G/§H)
5. `table_aggregation` family (done; §C): hybrid becomes the default family with the
   `prog+chain+table` recipe
6. `consistency` family port
7. First multi-model leaderboard on the hybrid gauntlet → publish \$/correct with
   replay manifests → then the evolution loop
