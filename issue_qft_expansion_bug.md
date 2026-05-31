# Issue Title

Bug: default UCC compilation can catastrophically expand repeated QFT + inverse-QFT circuits

# Issue Description

## Summary

I found a case where the default UCC compilation pipeline appears to catastrophically expand a highly structured circuit instead of simplifying it.

The issue is reproducible on a repeated `QFT + inverse-QFT` workload at large scale. In this setting, baseline UCC expands a `100,000`-gate input circuit to roughly `968,784` gates.

I am opening this as a standalone issue following the suggestion in the previous discussion.

## Minimal Reproducible Example

The following Qiskit circuit builds a repeated `QFT + inverse-QFT` pattern with exactly `100,000` gates:

```python
import math
from qiskit import QuantumCircuit
import ucc


def qft_block(num_qubits: int) -> QuantumCircuit:
    qc = QuantumCircuit(num_qubits)
    for target in range(num_qubits):
        qc.h(target)
        for control in range(target + 1, num_qubits):
            qc.cp(math.pi / (2 ** (control - target)), control, target)

    for i in range(num_qubits // 2):
        qc.swap(i, num_qubits - 1 - i)

    for i in range(num_qubits // 2):
        qc.swap(i, num_qubits - 1 - i)

    for target in reversed(range(num_qubits)):
        for control in reversed(range(target + 1, num_qubits)):
            qc.cp(-math.pi / (2 ** (control - target)), control, target)
        qc.h(target)

    return qc


num_qubits = 8
block = qft_block(num_qubits)
repeats = 100000 // len(block.data)

circuit = QuantumCircuit(num_qubits)
for _ in range(repeats):
    circuit.compose(block, inplace=True)

compiled = ucc.compile(circuit, return_format="qiskit")

print("input gates:", len(circuit.data))
print("output gates:", len(compiled.data))
print("input depth:", circuit.depth())
print("output depth:", compiled.depth())
print("input gate types:", sorted(circuit.count_ops().keys()))
print("output gate types:", sorted(compiled.count_ops().keys()))
```

## Observed Result

On my side, this produces approximately:

- input gates: `100000`
- output gates: `968784`
- input depth: `40000`
- output depth: `276266`

The output is rewritten into a basis using `cx`, `ry`, and `rz`, but the total gate count and depth increase very substantially.

## Why This Looks Problematic

This workload is highly structured and contains repeated `QFT + inverse-QFT` patterns. Even if the compiler does not fully eliminate the structure, I would not expect such a severe increase in total gate count and depth from the default pipeline.

At minimum, this seems worth discussing as a potential issue in the current default compilation strategy for structured circuits.

## Additional Context

I also tested an experimental structure-aware pre-pass and observed much stronger behavior there, but I am intentionally not using that as the claim in this issue.

This issue is specifically about the behavior of the current default UCC pipeline on the reproducible example above.

## Environment

- Repository: `unitaryfoundation/ucc`
- Branch base: current upstream `main`
- Python: `3.12`
- UCC installed in a local `uv` environment
