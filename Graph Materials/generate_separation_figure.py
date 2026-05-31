import os
import matplotlib.pyplot as plt
import numpy as np

# Data extracted from TeX draft and JSON results for `fourier_phase_sandwich`
x_input_gates = [4000, 10000, 20000, 50000, 100000]

# Panel A: Structural Quality (Output Gates)
y_optimized_ucc_gates = [42, 42, 42, 42, 42]
y_qiskit_opt3_gates = [9588, 23988, 47988, np.nan, np.nan] # Timeout at 50k, 100k
y_baseline_ucc_gates = [35117, 87916, 175832, 439580, 879160] # Linear extrapolation based on JSON

# Panel B: Runtime (Seconds)
y_optimized_ucc_time = [3.164, 14.621, 55.843, 20.129, 27.064]
y_qiskit_opt3_time = [1.397, 7.450, 29.5, np.nan, np.nan] # 20k approx, 50k+ timeout

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# --- Panel A: Structural Separation ---
ax1.plot(x_input_gates, y_optimized_ucc_gates, 'o-', color='#004488', label='Optimized UCC (Semantic)', linewidth=2.5)
ax1.plot(x_input_gates[:3], y_qiskit_opt3_gates[:3], '^-', color='#CC3311', label='Qiskit Opt3 (Flat/Local)', linewidth=2.5)
ax1.plot(x_input_gates, y_baseline_ucc_gates, 's--', color='#EE7733', alpha=0.7, label='Baseline UCC')

# Mark the timeout region
ax1.axvspan(35000, 105000, color='gray', alpha=0.15)
ax1.text(60000, 2000, "Flat Compiler\nTimeout", color='#CC3311', fontsize=11, fontweight='bold', ha='center')

ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.set_xlabel('Input Circuit Size (Gates)', fontsize=12)
ax1.set_ylabel('Compiled Output Size (Gates)', fontsize=12)
ax1.set_title('A. Structural Separation ($O(1)$ vs $\Omega(r)$)', fontsize=13)
ax1.grid(True, which="both", ls="--", alpha=0.4)
ax1.legend()

# --- Panel B: Computational Scalability ---
ax2.plot(x_input_gates, y_optimized_ucc_time, 'o-', color='#004488', label='Optimized UCC', linewidth=2.5)
ax2.plot(x_input_gates[:3], y_qiskit_opt3_time[:3], '^-', color='#CC3311', label='Qiskit Opt3', linewidth=2.5)

# Mark timeout threshold
ax2.axhline(90, color='black', linestyle=':', alpha=0.6)
ax2.text(4500, 95, "Timeout Threshold (>90s)", fontsize=10, color='black')
ax2.axvspan(35000, 105000, color='gray', alpha=0.15)

ax2.set_xscale('log')
ax2.set_xlabel('Input Circuit Size (Gates)', fontsize=12)
ax2.set_ylabel('Compilation Time (Seconds)', fontsize=12)
ax2.set_title('B. Computational Scalability', fontsize=13)
ax2.grid(True, which="both", ls="--", alpha=0.4)
ax2.legend()

# Save the figure
plt.tight_layout()
output_filename = 'fourier_layer_separation.png'
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_filename)
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Successfully generated and saved figure to: {output_path}")
