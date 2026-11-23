#ifndef RESONATOR_ARRAY_H
#define RESONATOR_ARRAY_H

#include <complex.h>
#include <stddef.h>

typedef struct {
    size_t n;
    double frequency_hz;
    double coil_resistance_ohm;
    double self_inductance_h;
    double adjacent_mutual_h;
    double receiver_mutual_peak_h;
    double receiver_mutual_sigma_cells;
    double receiver_impedance_ohm;
    double receiver_impedance_x_ohm;
    double termination_ohm;
} resonator_array_params;

double resonator_array_mutual(double x_cells, const resonator_array_params *p);
double complex resonator_array_input_impedance(double x_cells,
                                               const resonator_array_params *p);
int resonator_array_write_curve(const char *path, double x0, double x1,
                                size_t samples, const resonator_array_params *p);

#endif
