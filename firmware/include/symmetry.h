// Thermal Symmetry Guard — embedded core.
//
// This is the same algorithm as the Python reference in
// src/thermal_symmetry_guard/, kept deliberately parallel so the two can be
// diffed by eye. Two deviations from the reference, both intentional:
//
//   * All maths is float, never fixed-point integers. The original mistake
//     worth avoiding here is scaling temperatures to integers and then raising
//     them to the fourth power: T_K x100 to the fourth is ~8e17, which
//     overflows int64 the moment you multiply by anything. This design never
//     computes a fourth power at all -- log() of a rise is the only transcend-
//     ental function used, and it stays comfortably inside float range.
//   * Storage is bounded at compile time. No heap, no std::vector.
#pragma once

#include <math.h>
#include <stdbool.h>
#include <stdint.h>

#define TSG_MAX_POINTS      8
#define TSG_WINDOW          64
#define TSG_TAU_SEGMENT     64
#define TSG_MIN_RISE_K      1.5f
#define TSG_MIN_PEERS       3
#define TSG_MAD_TO_SIGMA    1.4826f

typedef enum {
    TSG_WARMING_UP = 0,
    TSG_SYMMETRIC,
    TSG_COMMON_MODE_RISE,
    TSG_ASYMMETRIC_HOT,
    TSG_ASYMMETRIC_COLD,
    TSG_TAU_SHIFT,
    TSG_SENSOR_SUSPECT
} tsg_verdict_t;

const char *tsg_verdict_name(tsg_verdict_t v);

// Fixed-capacity rolling window with median/MAD.
typedef struct {
    float    buf[TSG_WINDOW];
    uint8_t  count;
    uint8_t  head;
    float    sigma_floor;
} tsg_window_t;

void  tsg_window_init(tsg_window_t *w, float sigma_floor);
void  tsg_window_push(tsg_window_t *w, float v);
bool  tsg_window_ready(const tsg_window_t *w);
bool  tsg_window_full(const tsg_window_t *w);
float tsg_window_center(const tsg_window_t *w);
float tsg_window_sigma(const tsg_window_t *w);
float tsg_window_z(const tsg_window_t *w, float v);

typedef struct {
    float high;
    float low;
    float slack;
    float limit;
} tsg_cusum_t;

void  tsg_cusum_init(tsg_cusum_t *c, float slack, float limit);
float tsg_cusum_feed(tsg_cusum_t *c, float z);
bool  tsg_cusum_tripped(const tsg_cusum_t *c);

// Cooldown time-constant estimator: slope of log(rise) against time.
typedef struct {
    float   t[TSG_TAU_SEGMENT];
    float   y[TSG_TAU_SEGMENT];
    uint8_t n;
    float   tau_s;          // 0.0f means "not yet known"
    float   baseline_tau_s;
} tsg_tau_t;

void  tsg_tau_init(tsg_tau_t *e);
void  tsg_tau_reset(tsg_tau_t *e);
float tsg_tau_feed(tsg_tau_t *e, float t_s, float log_rise, bool cooling);

typedef struct {
    char         point_id[12];
    tsg_window_t offset;     // learned per-point constant: absorbs emissivity
    tsg_window_t asym;       // spread of the differential signal when healthy
    tsg_cusum_t  cusum;
    tsg_tau_t    tau;
    float        last_log_rise;
    bool         has_last;
    bool         quarantined;
    uint8_t      missing_sweeps;
} tsg_channel_t;

typedef struct {
    tsg_verdict_t verdict;
    float         temp_c;
    float         rise_k;
    float         asymmetry;
    float         z;
    float         cusum;
    float         tau_s;
    float         tau_ratio;
} tsg_result_t;

// Double-exponential (Holt) smoother. Used for the group common-mode trend so
// that "is the whole group heating?" is judged from a smoothed slope rather
// than a single noisy sample-to-sample delta.
typedef struct {
    float   level;
    float   slope;
    float   last_t;
    float   alpha;
    float   beta;
    uint8_t n;
    bool    started;
} tsg_trend_t;

void  tsg_trend_init(tsg_trend_t *f, float alpha, float beta);
void  tsg_trend_feed(tsg_trend_t *f, float value, float t_s);
float tsg_trend_slope(const tsg_trend_t *f);

typedef struct {
    tsg_channel_t ch[TSG_MAX_POINTS];
    uint8_t       n;
    float         z_warn;
    float         tau_tolerance;
    float         learn_below_z;
    float         common_mode;
    tsg_trend_t   common_trend;
    bool          common_rising;
} tsg_group_t;

void tsg_group_init(tsg_group_t *g, float z_warn);
bool tsg_group_add(tsg_group_t *g, const char *point_id);

// One synchronous sweep. temp_c[i] / present[i] are indexed the same as the
// order points were added. Results are written to out[].
void tsg_group_update(tsg_group_t *g,
                      const float  *temp_c,
                      const bool   *present,
                      float         ambient_c,
                      float         t_s,
                      tsg_result_t *out);
