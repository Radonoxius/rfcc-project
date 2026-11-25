#include "resonator_array.h"

#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define RESONATOR_ARRAY_PI 3.141592653589793238462643383279502884

static double cabs2(double complex z) { return creal(z) * creal(z) + cimag(z) * cimag(z); }

/*
 * The paper's Figure 6 shows a smooth, nearly Gaussian coupling profile,
 * with a peak at coil centres and a small overlap at adjacent centres.
 * x_cells is measured in coil pitches.  The two nearest coils are retained,
 * as in equations (7)-(12) of the paper.
 */
double resonator_array_mutual(double x_cells, const resonator_array_params *p) {
    if (!p || !isfinite(x_cells) || !isfinite(p->receiver_mutual_peak_h) ||
        !isfinite(p->receiver_mutual_sigma_cells) ||
        p->receiver_mutual_sigma_cells <= 0.0) return NAN;
    double d = fabs(x_cells);
    return p->receiver_mutual_peak_h * exp(-(d * d) /
                                           (p->receiver_mutual_sigma_cells *
                                            p->receiver_mutual_sigma_cells));
}

static int solve_complex(double complex *a, double complex *b, size_t n) {
    for (size_t k = 0; k < n; ++k) {
        size_t pivot = k;
        double best = cabs2(a[k * n + k]);
        for (size_t r = k + 1; r < n; ++r) {
            double score = cabs2(a[r * n + k]);
            if (score > best) { best = score; pivot = r; }
        }
        if (best < 1e-28) return -1;
        if (pivot != k) {
            for (size_t c = k; c < n; ++c) {
                double complex t = a[k * n + c];
                a[k * n + c] = a[pivot * n + c];
                a[pivot * n + c] = t;
            }
            double complex t = b[k]; b[k] = b[pivot]; b[pivot] = t;
        }
        for (size_t r = k + 1; r < n; ++r) {
            double complex f = a[r * n + k] / a[k * n + k];
            for (size_t c = k + 1; c < n; ++c) a[r * n + c] -= f * a[k * n + c];
            b[r] -= f * b[k];
        }
    }
    for (size_t k = n; k-- > 0;) {
        double complex s = b[k];
        for (size_t c = k + 1; c < n; ++c) s -= a[k * n + c] * b[c];
        b[k] = s / a[k * n + k];
    }
    return 0;
}

double complex resonator_array_input_impedance(double x_cells,
                                               const resonator_array_params *p) {
    if (!p || p->n == 0 || p->n == SIZE_MAX || !isfinite(x_cells) ||
        !isfinite(p->frequency_hz) || p->frequency_hz <= 0.0 ||
        !isfinite(p->coil_resistance_ohm) ||
        !isfinite(p->self_inductance_h) ||
        !isfinite(p->adjacent_mutual_h) ||
        !isfinite(p->receiver_mutual_peak_h) ||
        !isfinite(p->receiver_mutual_sigma_cells) ||
        p->receiver_mutual_sigma_cells <= 0.0 ||
        !isfinite(p->receiver_impedance_ohm) ||
        !isfinite(p->receiver_impedance_x_ohm) ||
        !isfinite(p->termination_ohm)) return NAN + I * NAN;
    const size_t dim = p->n + 1; /* n array currents + receiver current */
    if (dim > SIZE_MAX / dim || dim * dim > SIZE_MAX / sizeof(double complex) ||
        dim > SIZE_MAX / sizeof(double complex)) return NAN + I * NAN;
    const double w = 2.0 * RESONATOR_ARRAY_PI * p->frequency_hz;
    double complex *a = calloc(dim * dim, sizeof(*a));
    double complex *b = calloc(dim, sizeof(*b));
    if (!a || !b) { free(a); free(b); return NAN + I * NAN; }

    /* Unit voltage applied to the first array resonator. */
    b[0] = 1.0;
    for (size_t j = 0; j < p->n; ++j) {
        a[j * dim + j] = p->coil_resistance_ohm;
        if (j + 1 < p->n) {
            double complex zmut = I * w * p->adjacent_mutual_h;
            a[j * dim + j + 1] = zmut;
            a[(j + 1) * dim + j] = zmut;
        }
    }
    a[(p->n - 1) * dim + (p->n - 1)] += p->termination_ohm;

    /* Receiver is between floor(x) and floor(x)+1, clipped at array ends. */
    double left = floor(x_cells);
    if (left < 0.0) left = 0.0;
    if (left > (double)p->n - 1.0) left = (double)p->n - 1.0;
    size_t i = (size_t)left;
    size_t j = i + 1 < p->n ? i + 1 : i;
    double mi = resonator_array_mutual(x_cells - (double)i, p);
    double mj = (j == i) ? 0.0 : resonator_array_mutual(x_cells - (double)j, p);
    double complex zr = p->receiver_impedance_ohm + I * p->receiver_impedance_x_ohm;
    a[(dim - 1) * dim + (dim - 1)] = zr;
    for (size_t q = 0; q < p->n; ++q) {
        double m = q == i ? mi : (q == j ? mj : 0.0);
        if (m != 0.0) {
            double complex zmr = I * w * m;
            a[q * dim + dim - 1] = zmr;
            a[(dim - 1) * dim + q] = zmr;
        }
    }
    if (solve_complex(a, b, dim) != 0 || cabs(b[0]) < 1e-30) {
        free(a); free(b); return NAN + I * NAN;
    }
    double complex zin = 1.0 / b[0];
    free(a); free(b);
    return zin;
}

int resonator_array_write_curve(const char *path, double x0, double x1,
                                size_t samples, const resonator_array_params *p) {
    if (!path || !p || samples < 2 || !isfinite(x0) || !isfinite(x1) ||
        p->n == 0 || !isfinite(p->frequency_hz) || p->frequency_hz <= 0.0 ||
        !isfinite(p->receiver_mutual_sigma_cells) ||
        p->receiver_mutual_sigma_cells <= 0.0) return EINVAL;
    FILE *f = fopen(path, "w");
    if (!f) return errno;
    int rc = 0;
    if (fprintf(f, "x_cells,re_ohm,im_ohm,magnitude_ohm,phase_deg\n") < 0)
        rc = EIO;
    for (size_t k = 0; k < samples; ++k) {
        double x = x0 + (x1 - x0) * (double)k / (double)(samples - 1);
        double complex z = resonator_array_input_impedance(x, p);
        if (!isfinite(creal(z)) || !isfinite(cimag(z))) { rc = EDOM; break; }
        if (fprintf(f, "%.12g,%.12g,%.12g,%.12g,%.12g\n", x, creal(z), cimag(z),
                    cabs(z), carg(z) * 180.0 / RESONATOR_ARRAY_PI) < 0) { rc = EIO; break; }
    }
    if (fclose(f) != 0 && rc == 0) rc = EIO;
    return rc;
}
