# Unitary Compiler Collection (UCC) - Research Workspace

This workspace contains the **Unitary Compiler Collection (UCC)**, a Python library for frontend-agnostic, high-performance compilation of quantum circuits. The current state of the workspace is centered around a research project investigating **Pre-Basis Structural Simplification** for large structured quantum circuits.

## Project Overview

The primary goal of UCC is to provide a unified interface for various quantum compilation frameworks (Qiskit, Cirq, PyTKET, etc.) and to implement advanced compilation passes that improve circuit quality and performance.

### Key Directories

-   **`ucc/`**: The main development directory for the UCC library. This version includes an "optimized branch" featuring bounded pre-basis structural preprocessing (e.g., inverse-aware cancellation, repeated-block detection).
-   **`ucc-main/`**: A reference or baseline version of the UCC compiler, used for comparative studies in the research.
-   **`ucc/research/`**: Contains scripts and results for benchmarking UCC against other compilers and evaluating the new structural optimization passes.
-   **`PaperDraft/`**, **`Paper/`**, **`draft.tex`**: LaTeX sources for the research paper "Toward Pre-Basis Structural Simplification for Large Structured Quantum Circuits".
-   **`Graph Materials/`**: Data and scripts for generating plots and diagrams for the paper.

## Tech Stack

-   **Language**: Python 3.12+
-   **Core Libraries**: `qiskit`, `qbraid`, `pytket`, `cirq`, `quimb`, `bqskit`
-   **Tooling**: `uv` (package management), `pytest` (testing), `ruff` (linting/formatting), `hatchling` (build backend).

## Building and Running

The project uses `uv` for managing the development environment.

### Setup

To set up the development environment for the main `ucc` directory:

```bash
cd ucc
uv sync --all-extras --all-groups
```

### Testing

Run the test suite using `pytest`:

```bash
cd ucc
uv run pytest
```

The main tests are located in `ucc/ucc/tests/test_compile.py`.

### Linting

Run `ruff` for linting and formatting:

```bash
cd ucc
uv run ruff check .
```

### Running Experiments

Experiments can be found in `ucc/research/`. For example, to run the real instance benchmarks:

```bash
cd ucc
uv run python research/compare_real_instances.py
```

## Research Context

The project is currently addressing issues where default compilation pipelines catastrophically expand structured circuits (like repeated QFT + inverse-QFT) when lowering to basis gates too early. The implementation in `ucc/ucc/compile.py` includes heuristics and structural analysis to prevent this.

### Important Implementation Files

-   **`ucc/ucc/compile.py`**: Contains the main `compile` function and the extensive structural simplification logic.
-   **`ucc/ucc/transpilers/ucc_defaults.py`**: Defines the default Qiskit-based pass managers used by UCC.
-   **`ucc/issue_qft_expansion_bug.md`**: Detailed report of the QFT expansion issue that the current optimizations aim to solve.

## Documentation

-   `ucc/README.md`: General project information and quickstart.
-   `ucc/CHANGELOG.md`: History of releases and changes.
-   `draft.tex`: The latest draft of the research paper describing the methodology and results.


# Working Context
- Always check `./DEV_CONTEXT.md` for the latest task updates and cross-tool synchronization notes before starting a new task.

# Runtime Rules
- NEVER execute heavy compute scripts (like research/ scaling tests) on the local host.
- ALWAYS provision a remote Cloud Sandbox for python execution.

