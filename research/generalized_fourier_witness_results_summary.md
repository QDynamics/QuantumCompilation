# Generalized Fourier Witness Suite Summary

## Overall Conclusion
Semantic Fourier-layer aggregation remains repetition-independent across width, topology, and angle-family axes.

## Analysis by Setup
Each setup is `(n_qubits, topology, angle_family)`.

- **Strict structural-quality wins**: `42/42`
- **No-worse quality points**: `42/42`
- **Runtime/scalability wins**: `14/42`
- **Total timeouts across all tools/runs**: `26`

## Interpretation
The results robustly generalize the Fourier-layer recoverability separation theorem beyond fixed instances. In every configuration tested (varying qubit width, diagonal phase network topology, and angle family), the `semantic_ucc` compiler achieved a strict structural-quality win over the `qiskit_opt3` baseline (`42/42` wins). Most importantly, `semantic_ucc` demonstrates perfect repetition-independence, outputting a constant number of gates for any number of structural repetitions, whereas standard flat-pipeline approaches (`qiskit_opt3`, `baseline_ucc`, etc.) either suffer catastrophic linear expansion or time out on larger instances. This provides comprehensive empirical backing for the claim that pre-basis structural aggregation is necessary to preserve and recover global phase-polynomial structures.