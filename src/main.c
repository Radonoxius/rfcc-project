#include "resonator_array.h"

#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static resonator_array_params defaults(void) {
    resonator_array_params p = {
        .n = 6, .frequency_hz = 108365.0, .coil_resistance_ohm = 2.0 * 3.141592653589793 * 85000.0 * 70e-6 / 300.0,
        .self_inductance_h = 70e-6, .adjacent_mutual_h = -2.6e-6,
        .receiver_mutual_peak_h = 8.3e-6, .receiver_mutual_sigma_cells = 0.61,
        .receiver_impedance_ohm = 40.0, .receiver_impedance_x_ohm = 10.0,
        .termination_ohm = 0.8
    };
    return p;
}

static int parse_double(const char *text, double *value) {
    char *end = NULL;
    errno = 0;
    double parsed = strtod(text, &end);
    if (errno || end == text || *end != '\0' || !isfinite(parsed)) return -1;
    *value = parsed;
    return 0;
}

static int parse_cells(const char *text, size_t *value) {
    char *end = NULL;
    errno = 0;
    unsigned long long parsed = strtoull(text, &end, 10);
    if (errno || end == text || *end != '\0' || parsed == 0 || parsed > SIZE_MAX - 1)
        return -1;
    *value = (size_t)parsed;
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s curve.csv [cells] [termination_ohm] [receiver_r] [receiver_x]\n", argv[0]);
        return 2;
    }
    if (argc > 6) {
        fprintf(stderr, "too many arguments\n");
        return 2;
    }
    resonator_array_params p = defaults();
    if ((argc > 2 && parse_cells(argv[2], &p.n)) ||
        (argc > 3 && parse_double(argv[3], &p.termination_ohm)) ||
        (argc > 4 && parse_double(argv[4], &p.receiver_impedance_ohm)) ||
        (argc > 5 && parse_double(argv[5], &p.receiver_impedance_x_ohm))) {
        fprintf(stderr, "invalid numeric argument\n");
        return 2;
    }
    int rc = resonator_array_write_curve(argv[1], 0.0, (double)p.n - 1.0, 6001, &p);
    if (rc) { errno = rc; perror(argv[1]); return 1; }
    fprintf(stderr, "wrote %s (n=%zu, ZT=%.6g ohm, Zr=%.6g%+.6gj ohm)\n", argv[1], p.n,
            p.termination_ohm, p.receiver_impedance_ohm, p.receiver_impedance_x_ohm);
    return 0;
}
