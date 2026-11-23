# Receiver coil location detection for resonator arrays

This project implements the circuit model and position sensing approach described in:

> Mattia Simonazzi, Leonardo Sandrolini, and Andrea Mariscotti, “Receiver–Coil Location Detection in a Dynamic Wireless Power Transfer System for Electric Vehicle Charging,” *Sensors*, 22(6), 2317, 2022. DOI: [10.3390/s22062317](https://doi.org/10.3390/s22062317).

The project models a longitudinal array of magnetically coupled resonators. A small test signal is applied to the first cell at the selected frequency. The receiver changes the array's input impedance according to its position; the model calculates this impedance, and a position estimate can be obtained by comparing a measured impedance magnitude with a calibrated curve.

The numerical circuit solver and curve generation are written in C. Small Python utilities plot the curves and demonstrate position tracking from CSV measurements.

## Contents

```text
include/resonator_array.h  Public parameter structure and solver functions
src/resonator_array.c      Circuit equations, complex solver, and CSV curve writer
src/main.c                 Command-line program and default paper-case parameters
scripts/run_replication.sh Generate the included termination and array-size cases
scripts/plot_results.py    Plot generated impedance curves (requires matplotlib)
scripts/locate.py          Estimate positions from measured magnitudes and calibration
References/paper.pdf       Source paper
results/                   Generated CSV curves and plot
Makefile                   Build rules
```

## Model

The implementation follows the phasor Kirchhoff voltage equations for the array and receiver in equations (7) and (8) of the paper. It assembles the array currents and receiver current into a complex linear system, then solves it using Gaussian elimination with partial pivoting. With a unit voltage applied to the first cell, the input impedance is `Zin = 1 / I1`. This solves the same circuit represented by the paper's recursive impedance expressions (10)–(12), while directly modeling the coupled coils.

The array cells are coupled to their immediate neighbors. The receiver is coupled to the two adjacent array cells for its current position. Position `x_cells` is measured in coil pitches, with cell centers at integer coordinates. Each CSV curve contains 6,001 samples over the modeled array.

### Default parameter set

| Parameter | Default | Description |
| --- | ---: | --- |
| Array cells | 6 | Number of primary resonators |
| Test frequency | 108.365 kHz | Measurement frequency `f1` |
| Primary self inductance | 70 µH | `L` from Table 1 |
| Adjacent mutual inductance | −2.6 µH | `M` from Table 1 |
| Primary resistance | 0.1246 Ω | Derived from `R = 2π f0 L / Q`, with `f0 = 85 kHz`, `Q = 300` |
| Receiver impedance | 40 + j10 Ω | Series-compensated test case from Section 3.2 |
| Receiver coupling peak | 8.3 µH | Approximate peak read from Figure 6 |
| Receiver profile width | 0.61 coil pitches | Smooth profile calibration parameter |
| Termination impedance | 0.8 Ω | The paper's example termination for univocal behavior |

### Coupling-profile limitation

The paper plots receiver-to-array mutual inductance in Figure 6 but does not provide its sampled data, coil geometry, or an equation for that curve. `resonator_array_mutual()` therefore uses a smooth Gaussian-shaped approximation calibrated to the plotted peak and overlap. It is a reproducible modeling assumption, not a recovered exact geometry model. For quantitative replication with a particular coil design, replace that function with measured, finite-element, or otherwise validated mutual-inductance data. The other circuit parameters can be adjusted in the `resonator_array_params` structure.

## Requirements

For a basic build and CSV generation on Ubuntu or Debian:

```sh
sudo apt update
sudo apt install build-essential
```

Python is not needed for the C solver. To create the plot, install Python 3 and Matplotlib, for example:

```sh
sudo apt install python3 python3-matplotlib
```

## Build

From the project root:

```sh
make
```

This builds the `rfcc` executable. To remove the executable, object files, and generated result files:

```sh
make clean
```

## Generate an impedance curve

The CLI accepts an output path and up to four optional circuit arguments:

```text
./rfcc OUTPUT.csv [ARRAY_CELLS] [TERMINATION_OHMS] [RECEIVER_R_OHMS] [RECEIVER_X_OHMS]
```

For example, generate the six-cell paper test case with 0.8 Ω termination and receiver impedance `40 + j10 Ω`:

```sh
mkdir -p results
./rfcc results/termination_0p8.csv 6 0.8 40 10
```

Omitted arguments use the defaults listed above. `TERMINATION_OHMS` is modeled as a real resistance. `RECEIVER_R_OHMS` and `RECEIVER_X_OHMS` are the real and imaginary parts of the receiver impedance in ohms. The program reports the selected settings to stderr.

The output is a header row followed by these columns:

| Column | Meaning |
| --- | --- |
| `x_cells` | Receiver position in coil pitches |
| `re_ohm` | Real part of calculated input impedance |
| `im_ohm` | Imaginary part of calculated input impedance |
| `magnitude_ohm` | Input impedance magnitude |
| `phase_deg` | Input impedance phase in degrees |

## Reproduce the included cases

Run the driver script from the project root:

```sh
./scripts/run_replication.sh
```

It builds the executable if needed and writes these curves under `results/` :

| File | Array size | Termination |
| --- | ---: | ---: |
| `short.csv` | 6 cells | 0 Ω |
| `matched.csv` | 6 cells | 1.82 Ω (paper's listed matching impedance) |
| `open.csv` | 6 cells | 1,000,000,000 Ω, used as a numerical open-circuit approximation |
| `termination_0p8.csv` | 6 cells | 0.8 Ω |
| `termination_0p8_12cells.csv` | 12 cells | 0.8 Ω |

All five cases use the default receiver impedance `40 + j10 Ω`. If Python 3 and Matplotlib are available, the script creates separate, enlarged `results/curves_magnitude.png` and `results/curves_complex_plane.png` images; otherwise, CSV generation still completes and the plot step is skipped.

## Plot results

With Matplotlib installed, create separate, high-resolution images for every CSV file found in `results/`:

```sh
python3 scripts/plot_results.py results/curves
```

The script writes `results/curves_magnitude.png` for impedance magnitude against position and `results/curves_complex_plane.png` for the complex input impedance trajectory. The complex trajectory is useful for inspecting whether different positions produce similar impedance values; the paper discusses this univocity property in Section 3.3.

## Estimate positions from measurements

`scripts/locate.py` compares measured magnitudes with a generated calibration curve. The measurement CSV must include a column named `magnitude_ohm`, with one sample per row. For example:

```csv
magnitude_ohm
3.74
3.51
2.95
```

Run the locator with calibration settings matching the measurement setup:

```sh
python3 scripts/locate.py results/termination_0p8.csv measurements.csv > estimates.csv
```

The output is CSV-like text with no header and four fields: sample index, measured magnitude, estimated position in coil pitches, and absolute difference from the nearest calibration value. The script tracks the local interval using the direction of magnitude change, following the paper's basic derivative-based idea, then searches that interval for the closest calibration magnitude.

This locator is a small offline demonstration. It assumes consecutive samples move forward through the array and that the selected curve corresponds to the actual receiver, termination, and circuit settings. It does not currently model measurement noise, reverse travel, missed samples, or parameter drift. Use the full complex impedance and a noise-aware estimator when those effects matter.

## Using the C functions in another program

Include `resonator_array.h` and link with `src/resonator_array.c` and the math library. The `resonator_array_params` structure provides the array size, frequency, resistance and inductance values, receiver impedance and coupling-profile settings, and termination. The main functions are:

```c
double resonator_array_mutual(double x_cells, const resonator_array_params *params);
double complex resonator_array_input_impedance(double x_cells,
                                                const resonator_array_params *params);
int resonator_array_write_curve(const char *path, double x0, double x1,
                                size_t samples, const resonator_array_params *params);
```

The solver expects a positive array size and a valid coupling-profile width. It returns a complex NaN if memory allocation or the linear solve fails. The command-line interface is intended for curve generation; change the defaults in `src/main.c` when you need to sweep circuit properties not exposed as CLI arguments.

## Paper sections represented

- Sections 2–3: resonator array and receiver circuit model at the test frequency.
- Equations (7)–(12): coupled-circuit KVL and equivalent input impedance.
- Section 3.3: termination impedance and impedance trajectory behavior.
- Section 4.1: magnitude-based interval tracking concept.
- Section 4.2: position sensitivity is represented by the generated magnitude/phase curves; no dedicated sensitivity report is currently generated.

The work is a circuit-model reproduction, not a hardware implementation. Inverter parasitics, mutual coupling beyond adjacent primary cells, receiver motion-induced EMF, and measured sensor errors are outside the current model, consistent with the paper's simplifying assumptions.

## License

The repository includes a `LICENSE` file. The paper itself is open access under the Creative Commons Attribution license; consult the source paper for its reuse terms.
