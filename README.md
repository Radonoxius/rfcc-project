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
scripts/receiver_position_tracker.py           Noise-aware complex-impedance particle-filter tracker
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

This builds the `resonator-array` executable. To remove the executable, object files, and generated result files:

```sh
make clean
```

## Generate an impedance curve

The CLI accepts an output path and up to four optional circuit arguments:

```text
./resonator-array OUTPUT.csv [ARRAY_CELLS] [TERMINATION_OHMS] [RECEIVER_R_OHMS] [RECEIVER_X_OHMS]
```

For example, generate the six-cell paper test case with 0.8 Ω termination and receiver impedance `40 + j10 Ω`:

```sh
mkdir -p results
./resonator-array results/termination_0p8.csv 6 0.8 40 10
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

It builds the executable if needed and writes these curves under `results/`:

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

This locator is a small offline demonstration. It assumes consecutive samples move forward through the array and that the selected curve corresponds to the actual receiver, termination, and circuit settings.

## Improvements made

This section describes the added `receiver-position-tracker` program and the reasoning behind its design. The original `resonator-array` circuit simulator and magnitude-based `scripts/locate.py` locator are preserved. The new program is an additional estimator for sequential measurements; it does not change the circuit model or claim to replace calibration against the real hardware.

### Background and motivation

The original locator compares each measured impedance magnitude with a calibration curve. Its direction-based interval logic is useful for a clean sequence that moves monotonically, but it can be sensitive to noise, ambiguity between positions with similar magnitudes, missed samples, or a reversal in travel. Magnitude also discards the phase information represented by the real and imaginary parts of the input impedance.

`receiver-position-tracker` uses both coordinates of the complex input impedance and the history of earlier observations. It maintains many possible positions, scores them against each observation, and carries the weighted hypotheses into the next sample using a motion model. This retains ambiguity when the impedance curve maps multiple positions to similar values and lets the temporal sequence help resolve it.

### Research basis

The estimator is inspired by Sanchez et al., “Inductive Power Transfer Coil Misalignment Perception and Correction for Wirelessly Recharging Underground Sensors,” *Sensors*, 25(2), 309 (2025), [doi:10.3390/s25020309](https://doi.org/10.3390/s25020309). That study uses sequential Monte Carlo particle filters to estimate hidden coil position from electrical measurements, represents candidate positions with weighted particles, and models measurement errors with a Gaussian likelihood. The present implementation adapts those ideas to a one-dimensional receiver moving along this project's array and uses the circuit model's complex input impedance as its observation.

The cited study uses different hardware, dimensions, sensors, and experiments. Its reported results do not establish the accuracy of this program. This is a research-inspired implementation, not a replication of that study or a validation against physical measurements.

### Data flow

There are two inputs:

1. **Calibration curve:** a CSV generated by `resonator-array`, with at least `x_cells`, `re_ohm`, and `im_ohm` columns. The CSV represents predicted input impedance at known receiver positions for one set of circuit parameters.
2. **Measurements:** a CSV with `re_ohm` and `im_ohm` columns. Each row is one observation in time order. These should be measured input impedance values using the same sign convention and measurement reference as the calibration.

For each row, the program predicts impedance at every particle's position by linearly interpolating between the two surrounding calibration samples. It updates the particle weights with the measurement likelihood, calculates summary estimates, and conditionally resamples the particles before processing the next row.

The process can be summarized as:

```text
calibration curve + ordered complex measurements
                    │
      initialize possible positions
                    │
       motion prediction (after row 1)
                    │
 compare measured and predicted complex impedance
                    │
 update and normalize particle weights
                    │
 mean / MAP / spread / effective particle count
                    │
 resample if effective count is low; continue
```

### Particle-filter model

Let particle `i` have position `xᵢ` and weight `wᵢ`. Positions are in coil pitches; integer positions correspond to coil centers, matching the circuit model's `x_cells` convention. The calibrated circuit response is the complex function

`h(x) = Re(Zin(x)) + j Im(Zin(x))`.

The measured row is `zₖ = zᵣ + j zᵢ`. For the first row, particles are initialized uniformly over the calibration's position range, so no starting position or travel direction is assumed. For subsequent rows, each particle receives a Gaussian random-walk motion step:

`xₖ = clamp(xₖ₋₁ + Normal(0, motion_sigma), x_min, x_max)`.

The measurement likelihood is an isotropic Gaussian in the complex plane. Up to a normalization constant, the particle's new weight is:

`wₖ ∝ wₖ₋₁ exp(-|zₖ - h(xₖ)|² / (2 noise_sigma²))`.

Here `|z - h|² = (Re(z)-Re(h))² + (Im(z)-Im(h))²`. The calculation uses log weights and subtracts the largest log weight before exponentiation, avoiding numerical underflow for ordinary inputs. Weights are normalized to sum to one.

After the update, the program reports:

- `estimate_cells`: posterior weighted mean position.
- `map_cells`: position of the highest-weight particle (a discrete approximation to the maximum a posteriori estimate).
- `std_cells`: posterior weighted standard deviation in coil pitches. This summarizes spread but does not describe a potentially multimodal posterior fully.
- `ess`: effective sample size, `1 / sum(wᵢ²)`. It ranges from approximately 1 to the particle count; a low value means a few particles carry most of the probability mass.

When `ess` falls below half the particle count, systematic resampling selects a new particle population according to the current weights. The resampled particles receive equal weights. Resampling is skipped when weights remain sufficiently distributed, which avoids resampling on every row. The pseudorandom generator is seeded for reproducible runs.

### Build and use

`make` builds the original C executable and copies the Python tracker to the project-root executable `receiver-position-tracker`. Python 3 is required to run the tracker. Example:

```sh
make
./resonator-array results/termination_0p8.csv 6 0.8 40 10
./receiver-position-tracker results/termination_0p8.csv measurements_complex.csv \
    --noise 0.03 --motion 0.08 --particles 2000 --seed 1 > estimates.csv
```

`receiver-position-tracker` accepts:

```text
receiver-position-tracker CALIBRATION.csv MEASUREMENTS.csv
           [--noise OHMS] [--motion CELLS] [--particles COUNT] [--seed INTEGER]
```

Defaults are `--noise 0.03`, `--motion 0.08`, `--particles 2000`, and `--seed 1`. `--noise` is the standard deviation for each of the real and imaginary coordinates, in ohms; it is not a relative percentage. `--motion` is the standard deviation of the position change between adjacent rows, in coil pitches. The motion parameter therefore depends on measurement cadence: when samples are farther apart in time or the receiver moves faster, increase it to permit larger steps. The particle count controls Monte Carlo resolution and runtime. The seed controls repeatability, not estimator quality.

Measurement example:

```csv
re_ohm,im_ohm
3.741,-0.282
3.688,-0.251
3.601,-0.218
```

Output is CSV on standard output, with a header and one row per measurement. Diagnostics and invalid-input messages are sent to standard error. The sample index starts at zero. The expected columns and numeric values must be finite; calibration positions must be unique and have at least two rows.

### Choosing parameters

The defaults are demonstration values, not fitted values from the included paper or a physical sensor. Estimate `--noise` from repeated measurements at a fixed known position, calculating the standard deviation separately for real and imaginary impedance coordinates. If the two coordinates have noticeably different noise, the current isotropic likelihood is a simplifying assumption; an extension could accept separate standard deviations or a full covariance matrix.

Estimate `--motion` from plausible displacement between consecutive measurement rows. Too small a value can make the filter lag behind or lose a real rapid move after it has concentrated around the previous position. Too large a value weakens continuity and can leave several ambiguous regions plausible. If measurement spacing changes, the motion model should reflect the new interval. The current model is a zero-mean random walk: it supports both forward and reverse travel, but does not model known velocity or acceleration.

Use enough particles to cover the position range and the degree of ambiguity in the calibration response. Higher counts generally improve the approximation at additional runtime. Re-run with different seeds if results appear sensitive to Monte Carlo sampling; with the same seed and same inputs the output is reproducible.

### Assumptions and limitations

- The calibration and measurements refer to the same frequency, array size, termination, receiver load, sensor reference plane, and other circuit settings. A mismatch can look like a position error.
- The calibration curve is the model's response. In this repository, the receiver mutual-inductance profile is a Gaussian approximation to the paper's plotted curve, not measured geometry data. Estimator precision cannot exceed calibration accuracy.
- The measurement noise is independent, Gaussian, and equal for real and imaginary coordinates. Correlated noise, outliers, phase wrapping in another measurement representation, and parameter drift are not modeled.
- The position is restricted to the calibration interval. Motion beyond its ends is clamped to the boundary; this can accumulate particle probability at an endpoint. Extend the calibration domain if the intended operating range is larger.
- The random-walk prior assumes consecutive rows are temporally adjacent samples with comparable spacing. Missing rows or variable sample periods should be reflected in `--motion` or handled by an extended motion model.
- Resampling can reduce particle diversity. The current implementation does not add post-resampling jitter, use a velocity state, detect lost tracks, or report separate credible intervals for multiple modes. `std_cells` alone can conceal a multimodal posterior, so inspect the impedance curve and sequence when an estimate is ambiguous.
- The program processes rows in order and does not require monotonic motion. It is an offline sequence estimator that emits each posterior summary as it advances; it does not perform a backward smoothing pass.
- This change affects position estimation only. The circuit solver and its simplifying assumptions remain as documented in `README.md`.

### Difference from the original locator

| Behavior | `scripts/locate.py` | `receiver-position-tracker` |
| --- | --- | --- |
| Observation | Impedance magnitude | Real and imaginary impedance |
| Sequence context | Direction-based local interval | Weighted position hypotheses and motion prior |
| Motion | Assumes forward travel | Supports forward, reverse, and stationary motion |
| Noise model | No explicit likelihood | Gaussian complex-plane measurement likelihood |
| Ambiguity | Chooses nearest point in selected interval | Retains multiple hypotheses until measurements disambiguate them |
| Uncertainty output | Difference from nearest calibration magnitude | Posterior spread and effective particle count |

The tracker requires more careful noise and motion settings and a complex measurement CSV. For a single magnitude sample or a simple monotonic, low-noise demonstration, the original locator remains appropriate.

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
