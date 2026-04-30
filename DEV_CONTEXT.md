# DEV_CONTEXT

## Workspace Target

Use this workspace:

```text
/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)
```

Do not use this other workspace for the current project:

```text
/Users/yangjinsey/Desktop/Unitary-Compiler-Collection
```

## Recommended Next Steps

1. Inspect `ucc/research/experiment_results_overview_cn.md` first.
2. Inspect `PaperDraft/ucc_paper_draft_latex.tex` second.
3. The width-axis scaling experiments (n=5, 6) have been integrated into the paper and overview.
4. A new `tab:width-axis-scaling` has been added to the paper draft showing $O(m)$ scaling.
5. External stress tests at larger widths (n=5, 6) confirm that PyZX and TKET still fail to recover the semantic form in the tested pipelines.
6. A correctness certificate experiment (45 cases: n=4,5,6; seeds 0-4; sizes 4k-20k) confirmed that semantic Fourier compression is unitarily equivalent to the original input (is_equivalent=True for all cases).
7. A small packaging fix was applied to `pyproject.toml` (removing the unimplemented `ucc` script).
8. If improving code, avoid broad new heuristics; isolate one family or one dispatch path and rerun the corresponding script.
9. If improving the paper, tighten claims around recoverability gap and avoid saying optimized UCC universally beats Qiskit.
10. If preparing a PR, split the current prototype into small upstreamable patches.
