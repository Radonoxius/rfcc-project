# Project explained in simple English

## What this project is for

Imagine a row of charging coils built into a road or floor. A vehicle has another coil underneath it. As the vehicle moves, its coil passes over the row. This project explores a simple question:

> Can we tell where the moving coil is by checking how the row of coils responds to a small electrical test signal?

The software creates a mathematical model of the coils, calculates the response at different positions, and can compare real or example measurements with those predictions. It is a computer model and set of analysis tools. It does not connect to charging hardware or read a sensor by itself.

## The main idea

The coils can affect one another through their magnetic fields. You do not need to know the field equations to follow the program. The useful idea is that the row behaves a little differently depending on where the moving coil is.

The program sends a tiny imaginary test signal into the first coil in its model. It calculates how much current would flow there. From voltage and current, it calculates **input impedance**: a number describing how hard the circuit is to drive at that moment. Think of it as a circuit fingerprint. The fingerprint changes as the receiver coil moves.

Because the signal is alternating, its response has two parts:

- `re_ohm`: the in-phase part. Roughly, this relates to energy being used or lost.
- `im_ohm`: the out-of-phase part. Roughly, this relates to energy being stored and returned by coils and capacitors.

Together, those two numbers are called the **complex impedance**. You can think of them as two coordinates describing one fingerprint. The program also reports `magnitude_ohm`, which compresses those two coordinates into a single size. Magnitude is simpler to use, but it throws away some information.

## A map, then a location guess

The workflow has two stages:

1. **Make a map:** calculate the circuit fingerprint at many known receiver positions. This is the calibration curve, saved as a CSV file.
2. **Use the map:** compare a measured fingerprint with the values in the curve to estimate the receiver position.

The position column is named `x_cells`. It is measured in **coil pitches**: one pitch is the distance from one coil center to the next. So `x_cells = 2` means the center of the third coil when counting from zero. Values between whole numbers mean the receiver is between coil centers.

The curve is like a lookup table: “At this position, the model predicts this fingerprint.” If two positions have very similar fingerprints, a single reading may not say clearly which one is correct. Looking at a sequence of readings can help.

## The programs

### `resonator-array`: build the calibration map

This is the main C program. It models the row of coils and writes a CSV curve. Build the project and create a six-coil example like this:

```sh
make
mkdir -p results
./resonator-array results/termination_0p8.csv 6 0.8 40 10
```

The arguments after the output filename are:

1. number of coils in the row (`6`)
2. resistance at the last coil (`0.8` ohms)
3. receiver resistance (`40` ohms)
4. receiver reactance (`10` ohms)

If these are omitted, the program uses its built-in example settings. The CSV contains 6,001 positions across the modeled row, with real part, imaginary part, magnitude, and angle for each position.

The model solves all the coil-current equations together. In plain terms, it accounts for neighboring coils influencing each other, then calculates the current at the first coil and turns that into input impedance. You do not need to run or understand the math solver to use the command.

### `scripts/locate.py`: simple magnitude-based locator

This is the original example locator. It needs:

- the calibration curve made by `resonator-array`;
- a measurement CSV with a `magnitude_ohm` column.

Example command:

```sh
python3 scripts/locate.py results/termination_0p8.csv measurements.csv > estimates.csv
```

For each measurement it prints a row containing the sample number, measured magnitude, estimated position, and how far the selected calibration magnitude was from the measurement. This locator follows changes in the measurements to choose a nearby section of the row. It is intended for a clean sequence moving forward. It can struggle with noise, ambiguous values, or reversing direction.

### `receiver-position-tracker`: newer sequence-based locator

This separate program uses both `re_ohm` and `im_ohm` instead of magnitude alone. It also considers the sequence of measurements over time. It keeps many possible positions (“particles”) and gives more weight to positions whose predicted fingerprint resembles the current measurement. A motion setting says how far the receiver is expected to move between readings.

Example:

```sh
./receiver-position-tracker results/termination_0p8.csv measurements_complex.csv \
    --noise 0.03 --motion 0.08
```

The measurement file needs `re_ohm` and `im_ohm` columns. Each row is one reading, in time order. The output has one row per reading:

- `estimate_cells`: the average position after considering the weighted possibilities.
- `map_cells`: the single position with the most weight.
- `std_cells`: how spread out the possible positions are. A larger value means less certainty.
- `ess`: a check of how many particles still meaningfully contribute. A low value means only a small number dominate.

The first reading starts with possible positions spread across the full calibration curve. Later readings use a random-walk motion assumption, which allows forward, reverse, or nearly still movement. This makes it more flexible than the original locator, though it needs sensible settings and matching calibration.

`--noise` describes expected measurement error in ohms. Increase it if readings are noisy; decrease it for cleaner measurements. `--motion` describes plausible movement between consecutive readings, in coil pitches. Increase it if the receiver can move farther between samples. The defaults are examples, not values measured from a real device. The same inputs and `--seed` value produce the same run.

## Other useful files

- `src/main.c`: default circuit settings and command-line arguments for `resonator-array`.
- `src/resonator_array.c`: the coil model, current solver, and CSV curve writer.
- `include/resonator_array.h`: the C interface and list of model settings.
- `scripts/run_replication.sh`: builds the curve examples for several last-coil termination values.
- `scripts/plot_results.py`: turns curve CSV files into pictures. It needs Python and Matplotlib.
- `scripts/visualize_3d.py`: opens an interactive 3D coil-layout view with a slider and highlights the modeled signal response at the selected position. It needs Matplotlib.
- `results/`: example curves and plots already in the repository.
- `References/paper.pdf`: the research paper that the original model is based on.
- `Makefile`: instructions used by `make` to build both command-line programs.
- Root-level `.sh` files: shortcuts for building, running the model, generating curves, locating positions, and opening the 3D view.

## Make plots and example curves

To create the included cases again:

```sh
./scripts/run_replication.sh
```

There are also short helper commands in the project root. For example, `./build.sh` compiles the programs, `./run_model.sh results/my_curve.csv` generates a curve with the default settings, `./generate_curves.sh` recreates the example cases, and `./visualize_3d.sh` opens the default interactive view. Use `./track_positions.sh` or `./locate_positions.sh` to run the two position estimators; each prints its required arguments if called without them.

To draw plots from CSV files:

```sh
python3 scripts/plot_results.py results/curves
```

The magnitude plot shows how the size of the fingerprint changes along the row. The complex-plane plot draws each fingerprint as a point with real and imaginary coordinates. If the path doubles back or passes close to itself, different positions may have similar fingerprints, which can make location harder.

To interactively explore a curve, run:

```sh
python3 scripts/visualize_3d.py results/termination_0p8.csv
```

Move the slider to move the red receiver coil along the blue row. The orange lines show which two array coils the circuit model treats as coupled to the receiver; line strength gives a visual hint of the approximate coupling profile. The two small charts mark the selected position on the predicted impedance-size and phase curves. This picture is a teaching schematic: it does not calculate or display the true magnetic field in three dimensions.

## What the numbers and units mean

- **Ohms (`ohm` or `Ω`):** the unit used for impedance and resistance.
- **Kilohertz (`kHz`):** thousands of signal cycles per second. The default test signal is about 108 thousand cycles per second.
- **Microhenries (`µH`):** a unit describing how strongly a coil responds to changing current.
- **Coil pitch (`cells`):** the distance between neighboring coil centers, used as the position unit.
- **Termination:** the electrical load placed at the end of the row. Changing it changes the fingerprint and can make positions easier or harder to distinguish.

## Important limits

The curve is a prediction, not a physical measurement. The receiver-to-row coupling shape is approximated with a smooth bell-shaped curve because the source paper does not provide exact geometry data. For a real charging lane, the calibration should be replaced or checked using measurements or a validated coil model.

The measurement and calibration must describe the same hardware and conditions: coil count, test frequency, termination, receiver load, and measurement setup. If those differ, the locator may mistake a circuit change for a position change. Neither locator automatically corrects for parameter drift, and the newer tracker has not been validated against real sensors in this project.

The original research context is receiver-coil location detection for dynamic wireless charging. If you want the technical equations and full parameter discussion, see `README.md` and `References/paper.pdf`; this explainer is meant to give the practical picture first.
