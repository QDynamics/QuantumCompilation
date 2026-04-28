# DEV_CONTEXT

## Workspace Target

Use this workspace:

```text
/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)
```

Do not use this other workspace for the current project:

```text
/Users/yangjinsey/Desktop/Test out PopQC#574
```

The active UCC repository is:

```text
/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/ucc
```

There is also a baseline/reference copy:

```text
/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/ucc-main
```

## Project Summary

This workspace studies a UCC compiler regression on structured quantum
circuits. The core claim is not that UCC is universally better than Qiskit.
The current claim is narrower:

Basis lowering can destroy recoverable high-level structure. A bounded
pre-basis semantic/structural controller can preserve repeated, inverse,
mirrored, diagonal-phase, phase-ladder, and Fourier-layer structure long enough
to avoid severe UCC regressions and recover or exceed `qiskit opt3` quality on
selected structured families.

The strongest current framing is:

```text
representation-dependent recoverability gap
```

## Current PRX-Style Theory State

The paper has been shifted from a UCC engineering story toward a general
representation-separation story. The current strongest claim is:

```text
basis lowering preserves unitary semantics, but can destroy bounded local
recoverability of globally meaningful Fourier/phase/conjugation structure.
```

The main theorem is now the Fourier-layer recoverability separation in:

```text
PaperDraft/ucc_paper_draft_latex.tex
ucc/research/quantum_paper_draft.md
ucc/research/representation_gap_claims.md
```

The theorem uses the family:

```text
C_{m,r} = H_Lambda D_m(theta)^r H_Lambda
```

with `D_m(theta)` a commuting diagonal phase layer. For a restricted flat
compiler class `F^{fl}_{w,b,rho}` that only sees the basis-lowered stream,
uses bounded local certificates, and cannot first reconstruct a global
phase-polynomial / diagonal IR, the theorem states:

```text
pg_B(A(L_B(C_{m,r}))) >= c r m - O(m)
```

where `pg_B` counts nontrivial retained phase-gadget atoms after lowering. A
pre-basis Fourier-layer semantic compiler aggregates coefficients and satisfies:

```text
pg_B(L_B(S(C_{m,r}))) <= C m
```

For fixed width `m = m0 > w`, this gives the direct separation:

```text
Omega(r) versus O(1)
```

The theorem has been hardened relative to the earlier proof sketch:

- it now defines the structural measure `pg_B`;
- it replaces the ad hoc "local certificate collision" assumption with
  periodic separated lowering plus bounded finite-alphabet local certification;
- it states that repeated local certificates cannot authorize bulk global
  aggregation unless the compiler reconstructs a semantic global IR;
- it states explicit constants `c` and `C`;
- it gives a formal proof with a semantic upper bound and a flat lower bound;
- it includes a fixed-width corollary tied to the `42`-gate experiment.

The `fourier_phase_sandwich` family should be described as a theorem witness,
not as an arbitrary synthetic toy. The paper now connects it to natural
algorithmic sources:

- QFT decomposes into Hadamard boundaries plus commuting controlled phase
  rotations.
- AQFT preserves the same structure while truncating small-angle phase terms.
- QPE contributes repeated controlled phase accumulation followed by an
  inverse-QFT stage.

The witness isolates the common semantic object from these algorithms:

```text
a bounded collection of commuting diagonal phase terms whose repeated use
should be aggregated by coefficient addition before basis materialization
```

The algorithmic QFT/AQFT/QPE experiments are therefore not the formal
separation itself. They are natural-source controls showing that the same
recoverability issue appears outside the minimal witness construction.

Current PRX narrative role split:

- Fourier-layer / `H D^r H` is the primary theorem and main separation witness.
- Mirrored/conjugation shells are secondary anti-regression and parity-recovery
  evidence; do not present them as the main external-baseline separation.
- UCC is the artifact and diagnostic testbed, not the main scientific object.
- Avoid universal optimizer-dominance language. The claim is selective
  representation-dependent recoverability, not "optimized UCC beats Qiskit".

Terminology contract for PRX-style writing:

- Use `representation-dependent recoverability gap` for the general principle.
- Use `Fourier-layer recoverability separation` for the main theorem.
- Use `minimal theorem witness` for `fourier_phase_sandwich` / fixed-width
  `H D^r H`.
- Use `semantic side` for compilers that reconstruct global phase-polynomial,
  ZX, diagonal-Hamiltonian, or equivalent semantic IRs.
- Use `restricted flat-recovery side` for bounded post-lowering pipelines with
  local certificates and no global diagonal lift.
- Use `secondary anti-regression / parity-recovery evidence` for
  mirrored/conjugation data.
- Do not write that the theorem proves Qiskit, TKET, or PyZX can never solve
  the family. It only explains the behavior of the tested configured pipelines
  when they do not perform the semantic global lift.

Results should be discussed by evidence role, not just benchmark source:

1. primary theorem witness,
2. external flat-pipeline behavior,
3. Fourier semantic-path ablation,
4. natural algorithm-source controls,
5. secondary mirrored/conjugation recoverability evidence.

As of the latest PRX hardening pass, the four previously missing PRX-facing
links are written into the main materials:

1. theorem hardening and operational classification boundary,
2. natural algorithmic source matrix,
3. multi-compiler external-pipeline failure matrix,
4. FTQC/resource-consequence interpretation.

Canonical summary:

```text
ucc/research/prx_hardening_summary.md
```

Canonical overview:

```text
ucc/research/experiment_results_overview_cn.md
```

Main paper draft:

```text
PaperDraft/ucc_paper_draft_latex.tex
```

Markdown paper draft:

```text
ucc/research/quantum_paper_draft.md
```

Chinese presentation:

```text
Paper/Report.tex
```

## Current Code State

Important modified code:

```text
ucc/ucc/compile.py
ucc/ucc/tests/test_compile.py
```

The implementation in `ucc/ucc/compile.py` has grown beyond a small pass. It
currently includes:

- bounded structural pre-simplification
- exact repeated-prefix and repeated-run detection
- inverse and mirrored/self-inverse block handling
- diagonal-phase span canonicalization
- phase-ladder / Fourier-layer semantic IR terms
- repeated-run backend-aware dispatch
- candidate selection against safer references
- small in-process caches for semantic and backend candidates

Important caution:

This is now a research prototype / paper artifact implementation. If preparing
an upstream UCC PR, split it into smaller pieces. Do not submit the full current
`compile.py` diff as one upstream PR without refactoring.

## Current Git State In `ucc/`

The UCC repo has many modified research outputs plus compiler changes. Run:

```bash
cd "/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/ucc"
git status --short
```

Tracked files currently deleted as intentional cleanup:

```text
research/acm_tqc_strengthening_plan.md
research/hardware_aware_seed_portfolio_summary.md
research/structured_pipeline_results_100k.json
```

These were removed because they were old/stale stage artifacts, not current
canonical evidence.

## Canonical Result Files

Start with:

```text
ucc/research/experiment_results_overview_cn.md
```

Main canonical summaries:

```text
ucc/research/real_instance_results_summary.md
ucc/research/mqt_bench_results_summary.md
ucc/research/supermarq_results_summary.md
ucc/research/hardware_aware_results_summary.md
ucc/research/runtime_optimization_progress.md
ucc/research/runtime_overheads_issue_summary.md
ucc/research/phase_ladder_positive_results_summary.md
ucc/research/qft_inverse_external_scaling_results_summary.md
ucc/research/noninverse_phase_ladder_scaling_results_summary.md
ucc/research/mirrored_conjugation_positive_results_summary.md
ucc/research/mirrored_conjugation_scaling_results_summary.md
ucc/research/hardware_qaoa_scaling_results_summary.md
```

Current headline results:

- Real Qiskit library instances: optimized UCC matches `qiskit opt3` quality on
  `phase_estimation_real`, `grover_real`, and `qaoa_real`, with runtime close to
  parity.
- MQT Bench: `mqt_qpeexact_32`, `mqt_qaoa_32`, and `mqt_grover_20` recover
  `qiskit opt3` quality or severe timeout regressions.
- QFT + inverse-QFT external scaling: `4k/10k/20k/50k/100k` all reduce to zero,
  with systematic runtime/scalability wins.
- Non-inverse Fourier-layer scaling: `fourier_phase_sandwich = H · D^r · H`
  gives `5/5` strict structural-quality wins over `qiskit opt3`; optimized UCC
  outputs `42` gates at all tested sizes, and qiskit times out at `50k/100k`.
- Hardware-aware: `hw_mqt_qaoa_20` is the clearest external-baseline win;
  `hw_mqt_qpeexact_20` is parity; `hw_mqt_grover_20` is a robustness /
  timeout-recovery case rather than a clean win.

## Experiment Scripts

Core frozen artifact entry point:

```text
ucc/research/run_frozen_artifact.py
```

Useful commands:

```bash
cd "/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/ucc"
./.venv/bin/python research/run_frozen_artifact.py --suite core
./.venv/bin/python research/run_frozen_artifact.py --suite structured
./.venv/bin/python research/run_frozen_artifact.py --suite stability
```

Recent focused scripts:

```text
ucc/research/compare_phase_ladder_external_scaling.py
ucc/research/compare_noninverse_phase_ladder_scaling.py
ucc/research/compare_mirrored_conjugation_positives.py
ucc/research/compare_mirrored_conjugation_scaling.py
ucc/research/compare_hardware_qaoa_scaling.py
```

Artifact documentation:

```text
ucc/research/artifact_output_manifest.md
ucc/research/artifact_reproducibility_guide.md
ucc/research/artifact_environment_snapshot.md
```

## Paper Files

Main LaTeX paper draft:

```text
PaperDraft/ucc_paper_draft_latex.tex
PaperDraft/references.bib
PaperDraft/figures/
```

Compiled PDFs are kept:

```text
PaperDraft/ucc_paper_draft_latex.pdf
PaperDraft/out/ucc_paper_draft_latex.pdf
Paper/out/Report.pdf
```

Root-level older TeX drafts exist:

```text
draft.tex
plan.tex
plan_cn.tex
out/*.pdf
```

Do not treat root-level drafts as canonical unless explicitly requested. The
current paper should be read from `PaperDraft/ucc_paper_draft_latex.tex`.

## Cleanup Already Done

Removed generated files from the `#662(issue)` workspace:

- all `.DS_Store`
- Python `__pycache__` / `.pyc`
- `ucc/.pytest_cache`
- `ucc/.ruff_cache`
- `ucc/dist`
- `ucc/docs/source/_build`
- LaTeX auxiliary files: `.aux`, `.log`, `.out`, `.toc`, `.fls`,
  `.fdb_latexmk`, `.synctex.gz`, `.nav`, `.snm`, `.blg`, `.bbl`

Kept intentionally:

- `ucc/.venv/`, because it is the working experiment environment
- PDFs, TeX sources, BibTeX sources, figures, and RelatedWorks PDFs
- canonical JSON/MD experiment outputs
- current research scripts

## Validation Commands

For code-level sanity:

```bash
cd "/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/ucc"
./.venv/bin/python -m pytest ucc/tests/test_compile.py -q
./.venv/bin/python -m py_compile ucc/compile.py
```

For paper compilation:

```bash
cd "/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/PaperDraft"
xelatex -interaction=nonstopmode -output-directory=out ucc_paper_draft_latex.tex
```

If citations show `?`, run BibTeX or the existing local compile flow before
rerunning XeLaTeX.

## Recommended Next Steps

1. Inspect `ucc/research/experiment_results_overview_cn.md` first.
2. Inspect `PaperDraft/ucc_paper_draft_latex.tex` second.
3. Inspect `ucc/ucc/compile.py` only after understanding the paper claim.
4. If improving code, avoid broad new heuristics; isolate one family or one
   dispatch path and rerun the corresponding script.
5. If improving the paper, tighten claims around recoverability gap and avoid
   saying optimized UCC universally beats Qiskit.
6. If preparing a PR, split the current prototype into small upstreamable
   patches.
