#include "symmetry.h"

#include <string.h>

const char *tsg_verdict_name(tsg_verdict_t v) {
    switch (v) {
        case TSG_WARMING_UP:       return "warming_up";
        case TSG_SYMMETRIC:        return "symmetric";
        case TSG_COMMON_MODE_RISE: return "common_mode_rise";
        case TSG_ASYMMETRIC_HOT:   return "asymmetric_hot";
        case TSG_ASYMMETRIC_COLD:  return "asymmetric_cold";
        case TSG_TAU_SHIFT:        return "tau_shift";
        case TSG_SENSOR_SUSPECT:   return "sensor_suspect";
        default:                   return "unknown";
    }
}

// Insertion sort into a scratch buffer. n <= 64, runs once per channel per
// sweep at 0.25 Hz, so this is nowhere near a bottleneck.
static void sort_copy(const float *src, float *dst, uint8_t n) {
    memcpy(dst, src, n * sizeof(float));
    for (uint8_t i = 1; i < n; i++) {
        float key = dst[i];
        int8_t j = (int8_t)i - 1;
        while (j >= 0 && dst[j] > key) {
            dst[j + 1] = dst[j];
            j--;
        }
        dst[j + 1] = key;
    }
}

static float median_of(const float *v, uint8_t n) {
    if (n == 0) return 0.0f;
    float s[TSG_WINDOW];
    if (n > TSG_WINDOW) n = TSG_WINDOW;
    sort_copy(v, s, n);
    return (n & 1) ? s[n / 2] : 0.5f * (s[n / 2 - 1] + s[n / 2]);
}

void tsg_window_init(tsg_window_t *w, float sigma_floor) {
    memset(w, 0, sizeof(*w));
    w->sigma_floor = sigma_floor > 0.0f ? sigma_floor : 1e-4f;
}

void tsg_window_push(tsg_window_t *w, float v) {
    if (!isfinite(v)) return;
    w->buf[w->head] = v;
    w->head = (uint8_t)((w->head + 1) % TSG_WINDOW);
    if (w->count < TSG_WINDOW) w->count++;
}

bool tsg_window_ready(const tsg_window_t *w) { return w->count >= TSG_WINDOW / 4; }
bool tsg_window_full(const tsg_window_t *w)  { return w->count >= TSG_WINDOW; }

float tsg_window_center(const tsg_window_t *w) {
    return w->count ? median_of(w->buf, w->count) : 0.0f;
}

float tsg_window_sigma(const tsg_window_t *w) {
    if (w->count < 3) return w->sigma_floor;
    float c = tsg_window_center(w);
    float dev[TSG_WINDOW];
    for (uint8_t i = 0; i < w->count; i++) dev[i] = fabsf(w->buf[i] - c);
    float s = TSG_MAD_TO_SIGMA * median_of(dev, w->count);
    // The floor is not optional. Quantised sensor output produces windows with
    // MAD exactly zero, and an unfloored z would be infinite on the next LSB.
    return s > w->sigma_floor ? s : w->sigma_floor;
}

float tsg_window_z(const tsg_window_t *w, float v) {
    if (!isfinite(v)) return 0.0f;
    return (v - tsg_window_center(w)) / tsg_window_sigma(w);
}

void tsg_cusum_init(tsg_cusum_t *c, float slack, float limit) {
    c->high = c->low = 0.0f;
    c->slack = slack;
    c->limit = limit;
}

float tsg_cusum_feed(tsg_cusum_t *c, float z) {
    if (!isfinite(z)) z = 0.0f;
    c->high = fmaxf(0.0f, c->high + z - c->slack);
    c->low  = fminf(0.0f, c->low  + z + c->slack);
    return (c->high >= -c->low) ? c->high : c->low;
}

bool tsg_cusum_tripped(const tsg_cusum_t *c) {
    return c->high >= c->limit || -c->low >= c->limit;
}

void tsg_tau_init(tsg_tau_t *e) { memset(e, 0, sizeof(*e)); }
void tsg_tau_reset(tsg_tau_t *e) { e->n = 0; }

float tsg_tau_feed(tsg_tau_t *e, float t_s, float log_rise, bool cooling) {
    if (!cooling || !isfinite(log_rise)) { e->n = 0; return 0.0f; }
    if (e->n > 0 && (t_s - e->t[e->n - 1]) > 60.0f) e->n = 0;  // new episode
    if (e->n >= TSG_TAU_SEGMENT) {
        memmove(e->t, e->t + 1, (TSG_TAU_SEGMENT - 1) * sizeof(float));
        memmove(e->y, e->y + 1, (TSG_TAU_SEGMENT - 1) * sizeof(float));
        e->n = TSG_TAU_SEGMENT - 1;
    }
    e->t[e->n] = t_s;
    e->y[e->n] = log_rise;
    e->n++;

    if (e->n < 8) return 0.0f;
    float span = e->t[e->n - 1] - e->t[0];
    if (span < 30.0f) return 0.0f;
    if ((e->y[0] - e->y[e->n - 1]) < 0.15f) return 0.0f;

    float mx = 0.0f, my = 0.0f;
    for (uint8_t i = 0; i < e->n; i++) { mx += e->t[i]; my += e->y[i]; }
    mx /= e->n; my /= e->n;
    float sxx = 0.0f, sxy = 0.0f;
    for (uint8_t i = 0; i < e->n; i++) {
        float dx = e->t[i] - mx;
        sxx += dx * dx;
        sxy += dx * (e->y[i] - my);
    }
    if (sxx <= 0.0f) return 0.0f;
    float slope = sxy / sxx;
    if (slope >= 0.0f) return 0.0f;
    float tau = -1.0f / slope;
    if (!isfinite(tau) || tau <= 0.0f) return 0.0f;
    e->tau_s = tau;
    if (e->baseline_tau_s == 0.0f) e->baseline_tau_s = tau;
    return tau;
}

void tsg_trend_init(tsg_trend_t *f, float alpha, float beta) {
    memset(f, 0, sizeof(*f));
    f->alpha = alpha;
    f->beta = beta;
}

void tsg_trend_feed(tsg_trend_t *f, float value, float t_s) {
    f->n = (uint8_t)(f->n < 255 ? f->n + 1 : 255);
    if (!f->started) {
        f->level = value;
        f->slope = 0.0f;
        f->last_t = t_s;
        f->started = true;
        return;
    }
    float dt = t_s - f->last_t;
    if (dt < 1e-6f) dt = 1e-6f;
    float prev = f->level;
    f->level = f->alpha * value + (1.0f - f->alpha) * (prev + f->slope * dt);
    f->slope = f->beta * ((f->level - prev) / dt) + (1.0f - f->beta) * f->slope;
    f->last_t = t_s;
}

float tsg_trend_slope(const tsg_trend_t *f) {
    return (f->n >= 4) ? f->slope : 0.0f;   // warm-up, matches the reference
}

void tsg_group_init(tsg_group_t *g, float z_warn) {
    memset(g, 0, sizeof(*g));
    g->z_warn = z_warn;
    g->tau_tolerance = 0.25f;
    g->learn_below_z = 2.0f;
    tsg_trend_init(&g->common_trend, 0.3f, 0.1f);
}

bool tsg_group_add(tsg_group_t *g, const char *point_id) {
    if (g->n >= TSG_MAX_POINTS) return false;
    tsg_channel_t *c = &g->ch[g->n];
    memset(c, 0, sizeof(*c));
    strncpy(c->point_id, point_id, sizeof(c->point_id) - 1);
    tsg_window_init(&c->offset, 1e-4f);
    tsg_window_init(&c->asym, 0.01f);
    tsg_cusum_init(&c->cusum, 0.5f, 5.0f);
    tsg_tau_init(&c->tau);
    g->n++;
    return true;
}

void tsg_group_update(tsg_group_t *g,
                      const float  *temp_c,
                      const bool   *present,
                      float         ambient_c,
                      float         t_s,
                      tsg_result_t *out) {
    float lr[TSG_MAX_POINTS];
    bool  valid[TSG_MAX_POINTS];
    float usable[TSG_MAX_POINTS];
    uint8_t n_usable = 0;

    for (uint8_t i = 0; i < g->n; i++) {
        tsg_channel_t *c = &g->ch[i];
        valid[i] = false;
        lr[i] = 0.0f;
        if (!present[i]) {
            if (c->missing_sweeps < 255) c->missing_sweeps++;
            continue;
        }
        c->missing_sweeps = 0;
        float rise = temp_c[i] - ambient_c;
        if (!isfinite(rise) || rise < TSG_MIN_RISE_K) continue;
        lr[i] = logf(rise);
        valid[i] = true;
        if (!c->quarantined) {
            float off = tsg_window_full(&c->offset) ? tsg_window_center(&c->offset) : 0.0f;
            usable[n_usable++] = lr[i] - off;
        }
    }

    g->common_mode = n_usable ? median_of(usable, n_usable) : 0.0f;
    tsg_trend_feed(&g->common_trend, g->common_mode, t_s);
    g->common_rising = tsg_trend_slope(&g->common_trend) > 1e-4f;
    bool peer_quorum = n_usable >= TSG_MIN_PEERS;

    for (uint8_t i = 0; i < g->n; i++) {
        tsg_channel_t *c = &g->ch[i];
        tsg_result_t  *r = &out[i];
        memset(r, 0, sizeof(*r));
        r->temp_c = present[i] ? temp_c[i] : NAN;

        if (c->missing_sweeps >= 3) { r->verdict = TSG_SENSOR_SUSPECT; continue; }
        if (!present[i])            { r->verdict = TSG_SENSOR_SUSPECT; continue; }

        r->rise_k = temp_c[i] - ambient_c;
        if (!valid[i]) {
            r->verdict = TSG_WARMING_UP;
            c->has_last = false;
            continue;
        }

        bool  settled = tsg_window_full(&c->offset);
        float off = settled ? tsg_window_center(&c->offset) : 0.0f;
        float asym = (lr[i] - off) - g->common_mode;
        bool  scoring = settled && tsg_window_ready(&c->asym);
        float z = scoring ? tsg_window_z(&c->asym, asym) : 0.0f;
        float cs = scoring ? tsg_cusum_feed(&c->cusum, z) : 0.0f;

        bool cooling = c->has_last && lr[i] < c->last_log_rise;
        tsg_tau_feed(&c->tau, t_s, lr[i], cooling);
        float ratio = (c->tau.tau_s > 0.0f && c->tau.baseline_tau_s > 0.0f)
                          ? c->tau.tau_s / c->tau.baseline_tau_s
                          : 0.0f;

        r->asymmetry = asym;
        r->z = z;
        r->cusum = cs;
        r->tau_s = c->tau.tau_s;
        r->tau_ratio = ratio;

        if (!settled || !tsg_window_ready(&c->asym)) {
            r->verdict = TSG_WARMING_UP;
        } else if (ratio > 0.0f && fabsf(ratio - 1.0f) > g->tau_tolerance) {
            r->verdict = TSG_TAU_SHIFT;
        } else if (fabsf(z) >= g->z_warn || tsg_cusum_tripped(&c->cusum)) {
            r->verdict = (z > 0.0f || cs > 0.0f) ? TSG_ASYMMETRIC_HOT
                                                 : TSG_ASYMMETRIC_COLD;
            (void)peer_quorum;
        } else if (g->common_rising) {
            r->verdict = TSG_COMMON_MODE_RISE;
        } else {
            r->verdict = TSG_SYMMETRIC;
        }

        // Two-phase learning: fill the offset window first, then freeze it
        // against faults so a real hot spot never becomes the new normal.
        if (!settled) {
            tsg_window_push(&c->offset, lr[i] - g->common_mode);
        } else if (fabsf(z) < g->learn_below_z || !tsg_window_ready(&c->asym)) {
            tsg_window_push(&c->offset, lr[i] - g->common_mode);
            tsg_window_push(&c->asym, asym);
        }

        c->last_log_rise = lr[i];
        c->has_last = true;
    }
}
