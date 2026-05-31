# PRX Figure Materials

This directory contains the three current PRX-facing figures for the
representation-recoverability paper draft.  Each figure is generated from the
local experimental artifacts under `ucc/research` by:

```bash
ucc/.venv/bin/python "Graph Materials/generate_prx_figures.py"
```

The script writes both PNG previews and vector PDF versions.

## Figure 1: Fourier-Layer Separation

Files:

- `01_fourier_separation.png`
- `01_fourier_separation.pdf`

Data source:

- `ucc/research/noninverse_phase_ladder_scaling_results.json`

Purpose:

This figure is the main separation result.  It shows that the semantic UCC path
keeps the Fourier-layer witness at constant output size, while Qiskit and PyZX
grow with input size until timeout and TKET times out across the measured range.

## Figure 2: Resource Consequence

Files:

- `02_resource_consequence.png`
- `02_resource_consequence.pdf`

Data source:

- `ucc/research/resource_consequence_results.md`

Purpose:

This figure connects the representation gap to fault-tolerant resource
consequences.  It compares rotation multiplicity and a simple Clifford+T proxy
between semantic-first and materialize-first compilation.

## Figure 3: Fourier-Layer Ablation

Files:

- `03_fourier_ablation.png`
- `03_fourier_ablation.pdf`

Data source:

- `ucc/research/fourier_layer_ablation_results.md`

Purpose:

This figure isolates the mechanism: disabling the Fourier-layer semantic path
removes the constant-size behavior and produces timeouts, while the full
semantic path remains constant on the successful rows.

Note:

The ablation plot keeps the 20k all-timeout row visible as a runtime caveat
rather than hiding it.  This is intentional because it prevents overstating the
ablation result.
