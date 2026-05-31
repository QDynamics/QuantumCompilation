from qbraid.programs.alias_manager import get_program_type_alias
from qbraid.transpiler import ConversionGraph
from qbraid.transpiler import transpile as translate
from qiskit import transpile as qiskit_transpile
from qiskit.circuit import CircuitInstruction
from qiskit.circuit import QuantumCircuit as QiskitCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import CommutativeInverseCancellation
from .transpilers.ucc_defaults import UCCDefault1

import sys
import warnings

# Specify the supported Python version range
REQUIRED_MAJOR = 3
MINOR_VERSION_MIN = 12
MINOR_VERSION_MAX = 13

current_major = sys.version_info.major
current_minor = sys.version_info.minor

if current_major != REQUIRED_MAJOR or not (
    MINOR_VERSION_MIN <= current_minor <= MINOR_VERSION_MAX
):
    warnings.warn(
        f"Warning: This package is designed for Python {REQUIRED_MAJOR}.{MINOR_VERSION_MIN}-{REQUIRED_MAJOR}.{MINOR_VERSION_MAX}. "
        f"You are using Python {current_major}.{current_minor}."
    )
supported_circuit_formats = ConversionGraph().nodes()
_MAX_STRUCTURAL_BLOCK_SIZE = 256
_MIN_REPEATED_BLOCK_REPEATS = 4
_MAX_GLOBAL_STRUCTURAL_SCAN_SIZE = 50000
_MAX_FULL_PRESET_REFERENCE_SIZE = 20000
_MAX_PRESIMPLIFIED_FULL_PRESET_SIZE = 70000
_MAX_FULL_DIRECT_PRESET_SIZE = 120000
_MAX_DIRECT_SOURCE_PRESET_SIZE = 15000
_MIN_DIRECT_SOURCE_PRESET_SIZE = 2048
_FAST_PREFIX_SCAN_SIZE = 20000
_MIN_DOMINANT_REPEAT_FRACTION = 0.8
_MAX_REPEAT_MACRO_BLOCK_SIZE = 2048
_REPEAT_MACRO_FACTORS = (4, 2, 1)
_PARAMETER_MERGE_TOLERANCE = 1e-12
_MERGEABLE_PARAMETERIZED_GATES = {"rx", "ry", "rz", "p", "cp"}
_LOW_MULTI_QUBIT_FRACTION = 0.2
_DIRECT_SOURCE_DECOMPOSITION_RATIO = 20
_MEDIUM_DIRECT_SOURCE_DECOMPOSITION_RATIO = 2.5
_BACKEND_SEED_PORTFOLIO_OFFSETS = (0, 1, 2)
_MAX_BACKEND_SEED_PORTFOLIO_SIZE = 10000
_MAX_BACKEND_DEFAULT_PORTFOLIO_SIZE = 5000


def _translate_to_qiskit(circuit):
    """Translate to Qiskit, but skip qBraid when already in Qiskit format."""

    if isinstance(circuit, QiskitCircuit):
        return circuit
    return translate(circuit, "qiskit")


def _translate_from_qiskit(circuit, return_format):
    """Translate from Qiskit only when the caller asked for another format."""

    if return_format == "qiskit":
        return circuit
    return translate(circuit, return_format)


def _effective_target_gateset(target_gateset):
    """Resolve the all-to-all target gateset without constructing a compiler."""

    if target_gateset is not None:
        return set(target_gateset)
    return set(UCCDefault1.DEFAULT_GATESET)


def _build_circuit_from_instructions(template_circuit, instructions):
    """Build a new circuit with the same registers from a list of instructions."""

    rebuilt_circuit = template_circuit.copy_empty_like()
    rebuilt_circuit.global_phase = template_circuit.global_phase
    for instruction in instructions:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )
    return rebuilt_circuit


def _normalize_param(param):
    """Return a hashable representation for instruction parameters."""

    if isinstance(param, (int, float)):
        return round(float(param), 12)
    return str(param)


def _instruction_signature(circuit, instruction):
    """Compute a stable signature for repeated-block detection."""

    return (
        instruction.operation.name,
        tuple(
            _normalize_param(param) for param in instruction.operation.params
        ),
        tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits),
        tuple(circuit.find_bit(clbit).index for clbit in instruction.clbits),
    )


def _inverse_instruction_signature(circuit, instruction):
    """Compute the signature of an instruction's inverse when available."""

    try:
        inverse_operation = instruction.operation.inverse()
    except Exception:
        return None

    return (
        inverse_operation.name,
        tuple(_normalize_param(param) for param in inverse_operation.params),
        tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits),
        tuple(circuit.find_bit(clbit).index for clbit in instruction.clbits),
    )


def _copy_operation_with_parameter(operation, parameter):
    """Return a mutable copy of a single-parameter operation."""

    try:
        copied_operation = type(operation)(parameter)
    except Exception:
        copied_operation = (
            operation.to_mutable()
            if hasattr(operation, "to_mutable")
            else operation.copy()
        )
        copied_operation.params = [parameter]
    return copied_operation


def _can_merge_adjacent_parameterized_gates(left_instruction, right_instruction):
    """Return True when two adjacent single-parameter gates can be merged."""

    left_operation = left_instruction.operation
    right_operation = right_instruction.operation
    return (
        left_operation.name == right_operation.name
        and left_operation.name in _MERGEABLE_PARAMETERIZED_GATES
        and len(left_operation.params) == 1
        and len(right_operation.params) == 1
        and isinstance(left_operation.params[0], (int, float))
        and isinstance(right_operation.params[0], (int, float))
        and left_instruction.qubits == right_instruction.qubits
        and left_instruction.clbits == right_instruction.clbits
    )


def _merge_adjacent_parameterized_gates(circuit):
    """Merge adjacent additive rotation/phase gates on the same wires."""

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    pending_instruction = None

    def flush_pending_instruction():
        nonlocal pending_instruction
        if pending_instruction is None:
            return
        rebuilt_circuit.append(
            pending_instruction.operation,
            pending_instruction.qubits,
            pending_instruction.clbits,
        )
        pending_instruction = None

    for instruction in circuit.data:
        if pending_instruction is None:
            pending_instruction = instruction
            continue

        if _can_merge_adjacent_parameterized_gates(
            pending_instruction, instruction
        ):
            merged_parameter = float(
                pending_instruction.operation.params[0]
            ) + float(instruction.operation.params[0])
            if abs(merged_parameter) <= _PARAMETER_MERGE_TOLERANCE:
                pending_instruction = None
            else:
                pending_instruction = CircuitInstruction(
                    _copy_operation_with_parameter(
                        pending_instruction.operation, merged_parameter
                    ),
                    pending_instruction.qubits,
                    pending_instruction.clbits,
                )
            continue

        flush_pending_instruction()
        pending_instruction = instruction

    flush_pending_instruction()
    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _block_has_mergeable_parameter_repetitions(circuit, block_size):
    """Return True when a repeated block contains adjacent mergeable gates."""

    block_circuit = _build_circuit_from_instructions(
        circuit, list(circuit.data[:block_size])
    )
    return (
        len(_merge_adjacent_parameterized_gates(block_circuit).data)
        < len(block_circuit.data)
    )


def _block_has_self_inverse_boundary_overlap(circuit, block_size):
    """Return True when a block's suffix cancels with the next block's prefix."""

    return _find_self_inverse_prefix_suffix_overlap(circuit, block_size) > 0


def _run_commutative_inverse_cancellation(circuit):
    """Run Qiskit's commutative inverse cancellation when supported."""

    try:
        return PassManager([CommutativeInverseCancellation()]).run(circuit)
    except Exception:
        return circuit


def _has_nontrivial_composite_ops(circuit, target_gateset):
    """Return True when a circuit contains composite non-basis operations."""

    for instruction in circuit.data:
        operation = instruction.operation
        if operation.name in target_gateset or operation.name in {
            "measure",
            "barrier",
        }:
            continue

        definition = getattr(operation, "definition", None)
        if definition is not None and len(definition.data) > 1:
            return True

    return False


def _should_direct_short_circuit_qiskit_source_preset(
    source_circuit, target_gateset, target_backend, has_custom_passes
):
    """Return True when a qiskit-source circuit should go straight to opt3.

    This avoids paying extra wrapper overhead on medium-sized composite-source
    circuits where the optimized branch would ultimately defer to a source-level
    preset transpilation anyway.
    """

    if (
        target_backend is not None
        or has_custom_passes
        or not isinstance(source_circuit, QiskitCircuit)
    ):
        return False

    source_gate_count = len(source_circuit.data)
    if source_gate_count == 0 or source_gate_count > _MAX_DIRECT_SOURCE_PRESET_SIZE:
        return False

    return _has_nontrivial_composite_ops(source_circuit, target_gateset)


def _find_repeated_run(
    circuit,
    max_block_size=_MAX_STRUCTURAL_BLOCK_SIZE,
    min_repeats=_MIN_REPEATED_BLOCK_REPEATS,
):
    """Detect the largest repeated exact block anywhere in a circuit."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // min_repeats)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        start_index = 0
        while start_index + min_repeats * block_size <= instruction_count:
            block = signatures[start_index : start_index + block_size]
            repeat_count = 1
            while (
                start_index + (repeat_count + 1) * block_size
                <= instruction_count
            ):
                candidate_start = start_index + repeat_count * block_size
                candidate_end = candidate_start + block_size
                if signatures[candidate_start:candidate_end] != block:
                    break
                repeat_count += 1

            coverage = repeat_count * block_size
            if repeat_count >= min_repeats and coverage > best_coverage:
                best_match = (start_index, block_size, repeat_count)
                best_coverage = coverage

            start_index += coverage if repeat_count > 1 else 1

    return best_match


def _find_repeated_prefix(
    circuit,
    max_block_size=_MAX_STRUCTURAL_BLOCK_SIZE,
    min_repeats=_MIN_REPEATED_BLOCK_REPEATS,
):
    """Detect the largest repeated exact prefix block in a circuit."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // min_repeats)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]

    if instruction_count > _FAST_PREFIX_SCAN_SIZE:
        best_match = None
        best_coverage = 0

        for block_size in range(max_candidate_size, 0, -1):
            max_coverage = block_size * (instruction_count // block_size)
            if max_coverage <= best_coverage:
                continue

            prefix = signatures[:block_size]
            repeat_count = 1
            while (repeat_count + 1) * block_size <= instruction_count:
                start_index = repeat_count * block_size
                end_index = start_index + block_size
                if signatures[start_index:end_index] != prefix:
                    break
                repeat_count += 1

            coverage = repeat_count * block_size
            if repeat_count >= min_repeats and coverage > best_coverage:
                best_match = (block_size, repeat_count)
                best_coverage = coverage
                if coverage == instruction_count:
                    break

        return best_match

    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        prefix = signatures[:block_size]
        repeat_count = 1
        while (repeat_count + 1) * block_size <= instruction_count:
            start_index = repeat_count * block_size
            end_index = start_index + block_size
            if signatures[start_index:end_index] != prefix:
                break
            repeat_count += 1

        coverage = repeat_count * block_size
        if repeat_count >= min_repeats and coverage > best_coverage:
            best_match = (block_size, repeat_count)
            best_coverage = coverage

    return best_match


def _simplify_repeated_prefix(circuit):
    """Simplify a repeated leading block once and reuse the result."""

    repeated_prefix = _find_repeated_prefix(circuit)
    if repeated_prefix is None:
        return circuit

    block_size, repeat_count = repeated_prefix
    run_end = block_size * repeat_count
    block_instructions = list(circuit.data[:block_size])
    block_circuit = _build_circuit_from_instructions(
        circuit, block_instructions
    )
    simplified_block = _run_commutative_inverse_cancellation(block_circuit)

    if len(simplified_block.data) >= block_size:
        return circuit

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    for _ in range(repeat_count):
        for instruction in simplified_block.data:
            rebuilt_circuit.append(
                instruction.operation,
                instruction.qubits,
                instruction.clbits,
            )

    for instruction in circuit.data[run_end:]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _find_self_inverse_prefix_suffix_overlap(circuit, block_size):
    """Return the overlap size when a block suffix cancels the next prefix."""

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data[:block_size]
    ]
    inverse_signatures = [
        _inverse_instruction_signature(circuit, instruction)
        for instruction in circuit.data[:block_size]
    ]
    max_overlap = min(block_size // 2, 64)
    for overlap in range(max_overlap, 0, -1):
        suffix = signatures[block_size - overlap : block_size]
        inverse_prefix = list(reversed(inverse_signatures[:overlap]))
        if any(signature is None for signature in inverse_prefix):
            continue
        if suffix == inverse_prefix:
            return overlap
    return 0


def _compress_repeated_prefix_boundary_cancellation(circuit):
    """Compress repeated prefixes when adjacent copies cancel at the boundary."""

    repeated_prefix = _find_repeated_prefix(circuit)
    if repeated_prefix is None:
        return circuit

    block_size, repeat_count = repeated_prefix
    if repeat_count < 2:
        return circuit

    overlap = _find_self_inverse_prefix_suffix_overlap(circuit, block_size)
    if overlap == 0:
        return circuit

    middle_start = overlap
    middle_end = block_size - overlap
    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase

    _append_instruction_sequence(rebuilt_circuit, circuit.data[:overlap])
    middle_instructions = circuit.data[middle_start:middle_end]
    for _ in range(repeat_count):
        _append_instruction_sequence(rebuilt_circuit, middle_instructions)
    _append_instruction_sequence(
        rebuilt_circuit, circuit.data[block_size - overlap : block_size]
    )
    _append_instruction_sequence(
        rebuilt_circuit, circuit.data[block_size * repeat_count :]
    )

    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _find_adjacent_inverse_blocks(
    circuit, max_block_size=_MAX_STRUCTURAL_BLOCK_SIZE
):
    """Detect the largest adjacent exact block followed by its inverse."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // 2)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    inverse_signatures = [
        _inverse_instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        for start_index in range(0, instruction_count - 2 * block_size + 1):
            block = signatures[start_index : start_index + block_size]
            inverse_block = list(
                reversed(
                    inverse_signatures[
                        start_index + block_size : start_index + 2 * block_size
                    ]
                )
            )
            if any(signature is None for signature in inverse_block):
                continue
            if block != inverse_block:
                continue

            coverage = 2 * block_size
            if coverage > best_coverage:
                best_match = (start_index, block_size)
                best_coverage = coverage

    return best_match


def _simplify_repeated_run(circuit):
    """Simplify a repeated block once and reuse the result."""

    repeated_run = _find_repeated_run(circuit)
    if repeated_run is None:
        return circuit

    start_index, block_size, repeat_count = repeated_run
    run_end = start_index + block_size * repeat_count
    block_instructions = list(
        circuit.data[start_index : start_index + block_size]
    )
    block_circuit = _build_circuit_from_instructions(
        circuit, block_instructions
    )
    simplified_block = _run_commutative_inverse_cancellation(block_circuit)

    if len(simplified_block.data) >= block_size:
        return circuit

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    for instruction in circuit.data[:start_index]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    for _ in range(repeat_count):
        for instruction in simplified_block.data:
            rebuilt_circuit.append(
                instruction.operation,
                instruction.qubits,
                instruction.clbits,
            )

    for instruction in circuit.data[run_end:]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _cancel_adjacent_inverse_blocks(circuit):
    """Remove an adjacent block and its exact inverse."""

    inverse_block = _find_adjacent_inverse_blocks(circuit)
    if inverse_block is None:
        return circuit

    start_index, block_size = inverse_block
    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase

    for instruction in circuit.data[:start_index]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    for instruction in circuit.data[start_index + 2 * block_size :]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    return rebuilt_circuit


def _structural_pre_simplify(circuit):
    """Apply cheap structure-aware simplifications before basis lowering.

    Layer 1 uses commutative inverse cancellation directly on the whole
    circuit. Layer 2 simplifies large repeated exact blocks anywhere in the
    circuit. Layer 3 removes adjacent exact inverse blocks as whole units.
    """

    simplified_circuit = circuit
    for _ in range(3):
        previous_instruction_count = len(simplified_circuit.data)
        simplified_circuit = _merge_adjacent_parameterized_gates(
            simplified_circuit
        )
        simplified_circuit = _compress_repeated_prefix_boundary_cancellation(
            simplified_circuit
        )
        prefix_simplified_circuit = _simplify_repeated_prefix(
            simplified_circuit
        )
        if len(prefix_simplified_circuit.data) < len(simplified_circuit.data):
            simplified_circuit = prefix_simplified_circuit
        elif len(simplified_circuit.data) <= _MAX_GLOBAL_STRUCTURAL_SCAN_SIZE:
            simplified_circuit = _simplify_repeated_run(simplified_circuit)
            simplified_circuit = _cancel_adjacent_inverse_blocks(
                simplified_circuit
            )
        simplified_circuit = _run_commutative_inverse_cancellation(
            simplified_circuit
        )
        if len(simplified_circuit.data) >= previous_instruction_count:
            break
    return simplified_circuit


def _circuit_metrics(circuit):
    """Compute coarse structural metrics for anti-regression checks."""

    total_gates = 0
    multi_qubit_gates = 0
    for instruction in circuit.data:
        operation = instruction.operation
        if operation.name == "barrier":
            continue
        total_gates += 1
        if operation.num_qubits > 1 and operation.name != "measure":
            multi_qubit_gates += 1

    return {
        "total_gates": total_gates,
        "depth": circuit.depth(),
        "multi_qubit_gates": multi_qubit_gates,
    }


def _circuit_cost(circuit):
    """Score a circuit for conservative default-pipeline comparisons.

    The default compiler should not significantly inflate total size or depth
    in exchange for tiny multi-qubit improvements. This weighted score keeps
    two-qubit reductions valuable while still rejecting obvious blow-ups.
    """

    metrics = _circuit_metrics(circuit)
    return (
        metrics["total_gates"]
        + metrics["depth"]
        + 10 * metrics["multi_qubit_gates"]
    )


def _should_compare_against_preset(
    original_circuit, baseline_circuit, candidate_circuit
):
    """Return True when the default path shows a clear regression signal.

    Two cases justify the extra preset comparison:
    1. The UCC default flow is already worse than a simple basis translation.
    2. Basis lowering alone inflated the circuit enough that a more global
       optimizer may recover higher-level structure before decomposition.
    """

    baseline_cost = _circuit_cost(baseline_circuit)
    return _circuit_cost(
        candidate_circuit
    ) > baseline_cost or baseline_cost > 1.5 * _circuit_cost(original_circuit)


def _macro_repeat_candidates(circuit, block_size, repeat_count):
    """Yield bounded macro-repeat sizes for blockwise preset references."""

    yield 1

    block_has_parameter_merges = _block_has_mergeable_parameter_repetitions(
        circuit, block_size
    )
    block_has_boundary_overlap = _block_has_self_inverse_boundary_overlap(
        circuit, block_size
    )
    if not (block_has_parameter_merges or block_has_boundary_overlap):
        return

    for macro_repeat in _REPEAT_MACRO_FACTORS:
        if macro_repeat == 1:
            continue
        if macro_repeat > repeat_count:
            continue
        if block_size * macro_repeat > _MAX_REPEAT_MACRO_BLOCK_SIZE:
            continue
        if not block_has_parameter_merges and macro_repeat > 2:
            continue
        yield macro_repeat


def _append_instruction_sequence(circuit, instructions):
    """Append a sequence of instructions to a circuit."""

    for instruction in instructions:
        circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )


def _compile_repeated_prefix_reference(circuit, compiler, repeated_prefix):
    """Compile blockwise preset candidates for a dominant repeated prefix."""

    block_size, repeat_count = repeated_prefix
    coverage = block_size * repeat_count
    if coverage < _MIN_DOMINANT_REPEAT_FRACTION * len(circuit.data):
        return None

    candidate_circuits = []
    for macro_repeat in _macro_repeat_candidates(
        circuit, block_size, repeat_count
    ):
        macro_size = block_size * macro_repeat
        macro_circuit = _build_circuit_from_instructions(
            circuit, list(circuit.data[:macro_size])
        )
        macro_circuit = _structural_pre_simplify(macro_circuit)
        optimized_macro = qiskit_transpile(
            macro_circuit,
            basis_gates=list(compiler.target_gateset),
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )

        rebuilt_circuit = circuit.copy_empty_like()
        rebuilt_circuit.global_phase = circuit.global_phase
        full_macros, leftover_repeats = divmod(repeat_count, macro_repeat)
        for _ in range(full_macros):
            _append_instruction_sequence(
                rebuilt_circuit, optimized_macro.data
            )

        leftover_start = full_macros * macro_size
        leftover_end = leftover_start + leftover_repeats * block_size
        _append_instruction_sequence(
            rebuilt_circuit, circuit.data[leftover_start:leftover_end]
        )
        _append_instruction_sequence(rebuilt_circuit, circuit.data[coverage:])

        candidate_circuits.append(
            qiskit_transpile(
                rebuilt_circuit,
                basis_gates=list(compiler.target_gateset),
                optimization_level=0,
            )
        )

    if not candidate_circuits:
        return None

    return _select_lowest_cost_circuit(candidate_circuits)


def _should_compare_against_presimplified_preset(
    original_circuit, presimplified_circuit
):
    """Return True when a full opt3 run on the pre-simplified circuit is warranted."""

    if len(presimplified_circuit.data) > _MAX_PRESIMPLIFIED_FULL_PRESET_SIZE:
        return False

    original_metrics = _circuit_metrics(original_circuit)
    if original_metrics["total_gates"] == 0:
        return False

    reduction_fraction = 1 - (
        len(presimplified_circuit.data) / original_metrics["total_gates"]
    )
    multi_qubit_fraction = (
        original_metrics["multi_qubit_gates"] / original_metrics["total_gates"]
    )
    return (
        reduction_fraction >= 0.25
        and multi_qubit_fraction <= _LOW_MULTI_QUBIT_FRACTION
    )


def _compile_presimplified_full_preset_reference(circuit, compiler):
    """Compile a full opt3 reference on an already pre-simplified circuit."""

    if compiler.target_backend is not None:
        return _compile_backend_preset_portfolio(
            circuit,
            compiler,
            optimization_level=3,
        )

    return qiskit_transpile(
        circuit,
        basis_gates=list(compiler.target_gateset),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )


def _should_short_circuit_to_source_preset(
    source_circuit, translated_circuit, compiler
):
    """Return True when a source-level opt3 probe should bypass UCC default."""

    source_gate_count = len(source_circuit.data)
    if source_gate_count == 0:
        return False
    if source_gate_count > _MAX_DIRECT_SOURCE_PRESET_SIZE:
        return False

    translated_gate_count = len(translated_circuit.data)
    if (
        translated_gate_count
        >= _DIRECT_SOURCE_DECOMPOSITION_RATIO * source_gate_count
    ):
        return True

    if (
        source_gate_count >= _MIN_DIRECT_SOURCE_PRESET_SIZE
        and translated_gate_count
        >= _MEDIUM_DIRECT_SOURCE_DECOMPOSITION_RATIO * source_gate_count
    ):
        return True

    return (
        source_gate_count >= _MIN_DIRECT_SOURCE_PRESET_SIZE
        and _has_nontrivial_composite_ops(
            source_circuit, compiler.target_gateset
        )
    )


def _should_compare_against_direct_full_preset(
    original_circuit, presimplified_circuit, repeated_prefix
):
    """Return True when direct full opt3 is a cheaper dominant-repeat strategy."""

    if repeated_prefix is None:
        return False
    if len(original_circuit.data) > _MAX_FULL_DIRECT_PRESET_SIZE:
        return False
    if len(presimplified_circuit.data) != len(original_circuit.data):
        return False

    coverage = repeated_prefix[0] * repeated_prefix[1]
    return coverage >= _MIN_DOMINANT_REPEAT_FRACTION * len(original_circuit.data)


def _compile_preset_reference(circuit, compiler):
    """Compile a reference candidate with Qiskit's preset optimizer.

    This is only used as a fallback/reference for the default UCC pipeline, so
    it intentionally does not forward the user callback.
    """

    if compiler.target_backend is not None:
        return _compile_backend_preset_portfolio(
            circuit,
            compiler,
            optimization_level=3,
        )

    repeated_prefix = _find_repeated_prefix(circuit)
    if (
        len(circuit.data) > _MAX_FULL_PRESET_REFERENCE_SIZE
        and repeated_prefix is not None
    ):
        repeated_prefix_reference = _compile_repeated_prefix_reference(
            circuit, compiler, repeated_prefix
        )
        if repeated_prefix_reference is not None:
            return repeated_prefix_reference

    if len(circuit.data) > _MAX_FULL_PRESET_REFERENCE_SIZE:
        return None

    return qiskit_transpile(
        circuit,
        basis_gates=list(compiler.target_gateset),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )


def _select_lowest_cost_circuit(circuits):
    """Return the circuit with the lowest conservative structural cost."""

    return min(circuits, key=_circuit_cost)


def _dominates_structural_metrics(candidate_circuit, reference_circuit):
    """Return True when a candidate is no worse on core structural metrics."""

    candidate_metrics = _circuit_metrics(candidate_circuit)
    reference_metrics = _circuit_metrics(reference_circuit)
    if not (
        candidate_metrics["total_gates"] <= reference_metrics["total_gates"]
        and candidate_metrics["depth"] <= reference_metrics["depth"]
        and candidate_metrics["multi_qubit_gates"]
        <= reference_metrics["multi_qubit_gates"]
    ):
        return False

    return candidate_metrics != reference_metrics


def _backend_improvement_fraction(base_value, baseline_value):
    """Return the fractional reduction from a backend baseline to a candidate."""

    if baseline_value <= 0:
        return 0.0
    return max(0.0, (baseline_value - base_value) / baseline_value)


def _should_skip_backend_reference_probe(base_candidate, baseline_circuit):
    """Return True when the base backend candidate is already good enough.

    On some routed workloads, the default backend-aware UCC candidate already
    beats a cheap backend translation by a modest but consistent margin. In
    these cases, paying for an extra direct backend ``qiskit opt3`` probe tends
    not to change the final answer and only adds latency.
    """

    if baseline_circuit is None:
        return False
    if not _dominates_structural_metrics(base_candidate, baseline_circuit):
        return False

    base_metrics = _circuit_metrics(base_candidate)
    baseline_metrics = _circuit_metrics(baseline_circuit)
    return (
        _backend_improvement_fraction(
            base_metrics['total_gates'], baseline_metrics['total_gates']
        ) <= 0.05
        and _backend_improvement_fraction(
            base_metrics['depth'], baseline_metrics['depth']
        ) <= 0.15
        and _backend_improvement_fraction(
            base_metrics['multi_qubit_gates'],
            baseline_metrics['multi_qubit_gates'],
        ) <= 0.25
    )


def _backend_portfolio_seeds(compiler, circuit):
    """Return a small deterministic seed portfolio for backend-aware opt3."""

    base_seed = getattr(compiler, "seed_transpiler", None)
    if base_seed is None:
        return [None]
    if len(circuit.data) > _MAX_BACKEND_SEED_PORTFOLIO_SIZE:
        return [base_seed]
    return [base_seed + offset for offset in _BACKEND_SEED_PORTFOLIO_OFFSETS]


def _compile_backend_preset_portfolio(circuit, compiler, optimization_level):
    """Compile a small backend-aware preset portfolio and keep the best result."""

    candidates = []
    for seed in _backend_portfolio_seeds(compiler, circuit):
        candidates.append(
            qiskit_transpile(
                circuit,
                backend=compiler.target_backend,
                optimization_level=optimization_level,
                seed_transpiler=seed,
            )
        )
    return _select_lowest_cost_circuit(candidates)


def _compile_backend_default_portfolio(
    circuit,
    compiler,
    source_circuit=None,
    baseline_circuit=None,
    callback=None,
):
    """Run the backend-aware default pipeline over a small seed portfolio."""

    if (
        getattr(compiler, "seed_transpiler", None) is None
        or len(circuit.data) > _MAX_BACKEND_DEFAULT_PORTFOLIO_SIZE
        or callback is not None
    ):
        compiled_circuit = compiler.run(circuit, callback=callback)
        return _enforce_target_constraints(compiled_circuit, compiler)

    base_candidate = compiler.run(circuit, callback=callback)
    base_candidate = _enforce_target_constraints(base_candidate, compiler)

    if source_circuit is None:
        return base_candidate

    if _should_skip_backend_reference_probe(base_candidate, baseline_circuit):
        return base_candidate

    direct_backend_reference = qiskit_transpile(
        source_circuit,
        backend=compiler.target_backend,
        optimization_level=3,
        seed_transpiler=getattr(compiler, "seed_transpiler", None),
    )
    if _dominates_structural_metrics(base_candidate, direct_backend_reference):
        return base_candidate
    if _dominates_structural_metrics(direct_backend_reference, base_candidate):
        return direct_backend_reference

    candidates = [direct_backend_reference, base_candidate]
    portfolio_seeds = _backend_portfolio_seeds(compiler, circuit)
    for seed in portfolio_seeds[1:]:
        portfolio_compiler = UCCDefault1(
            target_backend=compiler.target_backend,
            target_gateset=compiler.target_gateset,
            seed_transpiler=seed,
        )
        candidate = portfolio_compiler.run(circuit)
        candidates.append(
            _enforce_target_constraints(candidate, portfolio_compiler)
        )

    return _select_lowest_cost_circuit(candidates)


def _enforce_target_constraints(circuit, compiler):
    """Re-translate a circuit into the requested backend or basis.

    Custom passes run after the default pipeline and may introduce operations
    outside the requested target. Run a final, non-optimizing translation so
    the public ``compile()`` contract still holds for the returned circuit.
    """

    if compiler.target_backend is not None:
        return qiskit_transpile(
            circuit,
            backend=compiler.target_backend,
            optimization_level=0,
            seed_transpiler=getattr(compiler, "seed_transpiler", None),
        )

    return qiskit_transpile(
        circuit,
        basis_gates=list(compiler.target_gateset),
        optimization_level=0,
    )


def compile(
    circuit,
    return_format="original",
    target_gateset=None,
    target_backend=None,
    custom_passes=None,
    callback=None,
    seed_transpiler=None,
):
    """Compiles the provided quantum `circuit` by translating it to a Qiskit
    circuit, transpiling it, and returning the optimized circuit in the
    specified `return_format`.

    Args:
        circuit (object): The quantum circuit to be compiled.
        return_format (str): The format in which your circuit will be returned.
            e.g., "TKET", "OpenQASM2". Check ``ucc.supported_circuit_formats``.
            Defaults to the format of the input circuit.
        target_gateset (set[str]): (optional) The gateset to compile the circuit to.
            e.g. {"cx", "rx",...}. Defaults to the gate set of the target device if available. If no `target_gateset` or ` target_backend` is provided, defaults to {"cx", "rz", "rx", "ry", "h"}.
        target_backend (qiskit.providers.backend): (optional)
            The target device  to compile the circuit for. Can be specified as a Qiskit backend. If None, all-to-all connectivity is assumed. If a `target_backend` is specified, `target_backend.operation_names` supercedes the `target_gateset`.
        custom_passes (list[qiskit.transpiler.TransformationPass]): (optional)
            A list of custom passes to apply after the default set
            of passes. Defaults to None.
        callback: A callback function that will be called after each pass execution. The
                function will be called with 5 keyword arguments::

                    pass_ (Pass): the pass being run
                    dag (DAGCircuit): the dag output of the pass
                    time (float): the time to execute the pass
                    property_set (PropertySet): the property set
                    count (int): the index for the pass execution
        seed_transpiler (int): (optional)
            Fixed seed forwarded to Qiskit's transpiler/preset manager. Useful
            for reproducible backend-aware experiments on the research branch.

    Returns:
        object: The compiled circuit in the specified format.
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)

    has_custom_passes = bool(custom_passes)

    # Translate to Qiskit Circuit object
    source_qiskit_circuit = _translate_to_qiskit(circuit)

    if _should_direct_short_circuit_qiskit_source_preset(
        source_qiskit_circuit,
        _effective_target_gateset(target_gateset),
        target_backend,
        has_custom_passes,
    ):
        direct_source_preset = qiskit_transpile(
            source_qiskit_circuit,
            basis_gates=list(_effective_target_gateset(target_gateset)),
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
        return _translate_from_qiskit(direct_source_preset, return_format)

    # Initialize the UCCDefault1 compiler with the target device and gateset
    ucc_default1 = UCCDefault1(
        target_backend=target_backend,
        target_gateset=target_gateset,
        seed_transpiler=seed_transpiler,
    )
    if (
        target_backend is None
        and not has_custom_passes
        and len(source_qiskit_circuit.data) <= _MAX_DIRECT_SOURCE_PRESET_SIZE
    ):
        source_basis_translated_circuit = qiskit_transpile(
            source_qiskit_circuit,
            basis_gates=ucc_default1.target_gateset,
            optimization_level=0,
        )
        if _should_short_circuit_to_source_preset(
            source_qiskit_circuit,
            source_basis_translated_circuit,
            ucc_default1,
        ):
            direct_source_preset = _compile_presimplified_full_preset_reference(
                source_qiskit_circuit, ucc_default1
            )
            if _circuit_cost(direct_source_preset) <= _circuit_cost(
                source_basis_translated_circuit
            ):
                return _translate_from_qiskit(
                    direct_source_preset, return_format
                )

    qiskit_circuit = _structural_pre_simplify(source_qiskit_circuit)

    if (
        target_backend is None
        and not has_custom_passes
        and _should_compare_against_presimplified_preset(
            source_qiskit_circuit, qiskit_circuit
        )
    ):
        final_result = _translate_from_qiskit(
            _compile_presimplified_full_preset_reference(
                qiskit_circuit, ucc_default1
            ),
            return_format,
        )
        return final_result

    repeated_prefix = None
    if (
        target_backend is None
        and not has_custom_passes
        and len(source_qiskit_circuit.data) > _MAX_FULL_PRESET_REFERENCE_SIZE
    ):
        repeated_prefix = _find_repeated_prefix(source_qiskit_circuit)

    if (
        target_backend is None
        and not has_custom_passes
        and _should_compare_against_direct_full_preset(
            source_qiskit_circuit, qiskit_circuit, repeated_prefix
        )
    ):
        final_result = _translate_from_qiskit(
            _compile_presimplified_full_preset_reference(
                source_qiskit_circuit, ucc_default1
            ),
            return_format,
        )
        return final_result

    # Translate into the target device gateset first; no optimization
    basis_translated_circuit = qiskit_transpile(
        qiskit_circuit,
        basis_gates=ucc_default1.target_gateset,
        optimization_level=0,
    )
    if target_backend is None:
        baseline_circuit = basis_translated_circuit
    else:
        baseline_circuit = _enforce_target_constraints(
            qiskit_circuit, ucc_default1
        )

    has_large_dominant_repeat = (
        target_backend is None
        and not has_custom_passes
        and repeated_prefix is not None
        and repeated_prefix[0] * repeated_prefix[1]
        >= _MIN_DOMINANT_REPEAT_FRACTION * len(source_qiskit_circuit.data)
        and len(source_qiskit_circuit.data) > 0
    )

    if has_large_dominant_repeat:
        candidate_circuits = [basis_translated_circuit]
        if _should_compare_against_presimplified_preset(
            source_qiskit_circuit, qiskit_circuit
        ):
            candidate_circuits.append(
                _compile_presimplified_full_preset_reference(
                    qiskit_circuit, ucc_default1
                )
            )
        else:
            preset_reference = _compile_preset_reference(
                source_qiskit_circuit, ucc_default1
            )
            if preset_reference is not None:
                candidate_circuits.append(preset_reference)
        compiled_circuit = _select_lowest_cost_circuit(candidate_circuits)
    else:
        # Compile the circuit using the UCCDefault1 pass manager
        if target_backend is not None and not has_custom_passes:
            compiled_circuit = _compile_backend_default_portfolio(
                basis_translated_circuit,
                ucc_default1,
                source_circuit=qiskit_circuit,
                baseline_circuit=baseline_circuit,
                callback=callback,
            )
        else:
            compiled_circuit = ucc_default1.run(
                basis_translated_circuit, callback=callback
            )
            compiled_circuit = _enforce_target_constraints(
                compiled_circuit, ucc_default1
            )

        if has_custom_passes:
            custom_pass_manager = PassManager()
            custom_pass_manager.append(custom_passes)
            compiled_circuit = custom_pass_manager.run(
                compiled_circuit, callback=callback
            )
            compiled_circuit = _enforce_target_constraints(
                compiled_circuit, ucc_default1
            )
        if not has_custom_passes:
            candidate_circuits = [baseline_circuit, compiled_circuit]
            if _should_compare_against_preset(
                source_qiskit_circuit, baseline_circuit, compiled_circuit
            ):
                preset_reference = _compile_preset_reference(
                    source_qiskit_circuit, ucc_default1
                )
                if preset_reference is not None:
                    candidate_circuits.append(preset_reference)
            if _should_compare_against_presimplified_preset(
                source_qiskit_circuit, qiskit_circuit
            ):
                candidate_circuits.append(
                    _compile_presimplified_full_preset_reference(
                        qiskit_circuit, ucc_default1
                    )
                )
            compiled_circuit = _select_lowest_cost_circuit(candidate_circuits)

    # Translate the compiled circuit to the desired format
    final_result = _translate_from_qiskit(compiled_circuit, return_format)
    return final_result
