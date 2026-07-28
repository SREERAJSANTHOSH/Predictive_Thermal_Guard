# Thermal Symmetry Guard — Mathematical Theory

This document derives the signal-processing pipeline behind the Thermal Symmetry Guard (TSG) algorithm from first principles. The goal is to detect **thermal asymmetry** — abnormal temperature differences between nominally identical points — using low-cost, uncalibrated infrared sensors.

---

## 1. Why Absolute IR Thermometry Fails in the Field

An infrared sensor does not measure temperature directly. It measures radiant power $W$ from a surface and converts it via the Stefan–Boltzmann law:

$$W = \varepsilon \, \sigma \, T^4$$

where $\varepsilon$ is the surface emissivity (0–1), $\sigma$ is the Stefan–Boltzmann constant, and $T$ is the true surface temperature in kelvin.

Three problems make absolute readings unreliable in practice:

1. **Unknown emissivity.** The sensor firmware assumes a fixed $\varepsilon$ (typically 0.95). Real surfaces — painted motor housings, oxidised cable lugs, dusty bus bars — vary from 0.2 to 0.98. A 10% emissivity error on a 350 K surface produces a ~9 K apparent error.

2. **Emissivity drift.** Dust accumulation, surface oxidation, and condensation change $\varepsilon$ over weeks. Any threshold set on absolute temperature drifts with it.

3. **$T^4$ nonlinearity.** Small emissivity errors are amplified by the fourth-power relationship. At 400 K, a 5% emissivity error maps to a ~21 K apparent error. Comparing raw temperatures between sensors with different $\varepsilon$ factors is meaningless.

> **Conclusion:** Absolute temperature thresholds are fragile. We need a measurement domain where emissivity cancels.

---

## 2. The Log-Transform Insight

### 2.1 Rise Above Ambient

Define the **temperature rise** above ambient:

$$\Delta T_{\text{true}} = T_{\text{surface}} - T_{\text{ambient}}$$

The sensor reports an apparent rise that is scaled by an unknown, slowly varying gain $g$ that encapsulates emissivity and optical-path losses:

$$\Delta T_{\text{apparent}} = g \cdot \Delta T_{\text{true}}$$

where $g \approx \varepsilon^{1/4}$ for small perturbations around the operating point (linearising the $T^4$ relationship).

### 2.2 Logarithmic Domain

Apply the natural logarithm:

$$\ln(\Delta T_{\text{apparent}}) = \ln(g) + \ln(\Delta T_{\text{true}})$$

The multiplicative gain $g$ becomes an **additive offset** $\ln(g)$. This is the key insight: in log-space, emissivity is a constant that can be subtracted.

### 2.3 Notation

Throughout this document we write:

$$x_i = \ln(\Delta T_{\text{apparent},\, i})$$

for the log-rise of the $i$-th measurement point.

---

## 3. Peer Subtraction

### 3.1 Exploiting Symmetry

In a balanced three-phase system driving $N$ identical loads (e.g., 6 VFDs on a common bus), nominally identical points should carry the same thermal load. Any common-mode effects — ambient temperature swings, shared airflow changes — affect all points equally.

Given $n$ peer points with log-rises $x_1, x_2, \ldots, x_n$, define the **peer median**:

$$\tilde{x} = \operatorname{median}(x_1, x_2, \ldots, x_n)$$

The **peer-subtracted residual** for point $i$ is:

$$r_i = x_i - \tilde{x}$$

This cancels:

- Common-mode ambient shifts (all $x_i$ shift together).
- Shared load changes (all true rises scale together).
- Sensor gain drift that is **uniform** across peers (unlikely, but still cancelled).

What remains is the **differential signal**: how much point $i$ deviates from its peers.

### 3.2 Why Median, Not Mean

The median is a robust estimator. If one point is genuinely faulty (hot), the mean is pulled toward the fault, diluting the anomaly. The median ignores up to $\lfloor n/2 \rfloor - 1$ outliers.

For 6 VFDs across 3 phases, we can tolerate up to 2 simultaneous faults before the median itself becomes unreliable.

---

## 4. Offset Subtraction (Learned Baseline)

After peer subtraction, a per-point residual bias remains:

$$r_i = \underbrace{\ln(g_i) - \ln(\tilde{g})}_{\text{static offset } c_i} + \underbrace{\ln(\Delta T_{\text{true},\, i}) - \ln(\widetilde{\Delta T_{\text{true}}})}_{\text{true differential signal}}$$

The static offset $c_i$ encodes the **residual emissivity difference** between point $i$ and the group. It is constant as long as the sensor's optical path and the surface condition do not change.

During a **learning phase** (commissioning), we accumulate peer-subtracted residuals under known-good conditions and compute:

$$\hat{c}_i = \operatorname{median}(r_i^{(1)}, r_i^{(2)}, \ldots, r_i^{(L)})$$

where $L$ is the number of learning samples. The **corrected residual** is:

$$r_i' = r_i - \hat{c}_i$$

After offset subtraction, $r_i'$ is zero-centred under normal operation. Any nonzero value is a genuine asymmetry signal.

---

## 5. What Survives: Pure Differential Mode

After the full pipeline — log transform → peer subtraction → offset subtraction — the corrected residual is:

$$r_i' = \ln\!\left(\frac{\Delta T_{\text{true},\, i}}{\widetilde{\Delta T_{\text{true}}}}\right) + \underbrace{(\ln(g_i) - \ln(\tilde{g})) - \hat{c}_i}_{\approx\, 0}$$

Under normal operation, $\Delta T_{\text{true},\, i} \approx \widetilde{\Delta T_{\text{true}}}$, so $r_i' \approx 0$.

Under a fault condition — a loose connection, blocked airflow, bearing failure — $\Delta T_{\text{true},\, i}$ rises relative to peers, and $r_i'$ grows proportionally (in log-space).

**What is detected:**
- Asymmetric heating (one point hotter than peers)
- Asymmetric cooling (one point cooler — e.g., a disconnected load)

**What is rejected:**
- Ambient temperature swings
- Uniform load changes
- Sensor gain (emissivity) differences
- Slow common-mode drift

This is a **differential mode** detector — it is sensitive only to asymmetry.

---

## 6. Robust Z-Scoring

### 6.1 Standard Z-Score and Its Fragility

The standard z-score normalises residuals by the group standard deviation:

$$z_i = \frac{r_i'}{\hat{\sigma}}$$

Using $\hat{\sigma} = \operatorname{std}(r')$ is fragile: a single outlier inflates $\hat{\sigma}$ and masks the fault.

### 6.2 Median Absolute Deviation (MAD)

The **median absolute deviation** is defined as:

$$\text{MAD} = \operatorname{median}\!\left(|r_i' - \operatorname{median}(r')|\right)$$

The robust scale estimate is:

$$\hat{\sigma}_{\text{MAD}} = 1.4826 \times \text{MAD}$$

The constant 1.4826 makes $\hat{\sigma}_{\text{MAD}}$ a consistent estimator of $\sigma$ for normal data. The MAD tolerates up to 50% contamination.

### 6.3 The Sigma Floor: Preventing Division by Zero

Quantised sensors (e.g., MLX90614 with 0.02 K resolution) frequently produce **identical** readings across peers, yielding $\text{MAD} = 0$ and therefore $\hat{\sigma}_{\text{MAD}} = 0$.

Dividing by zero produces infinite z-scores on any nonzero residual — a false alarm catastrophe.

**Solution:** enforce a mandatory sigma floor $\sigma_{\min}$:

$$\hat{\sigma} = \max(\hat{\sigma}_{\text{MAD}},\; \sigma_{\min})$$

A reasonable floor is $\sigma_{\min} = 0.01$ in log-rise units, corresponding to roughly 1% relative temperature difference. This ensures that quantisation noise never triggers an alarm.

### 6.4 Robust Z-Score Formula

The final robust z-score is:

$$z_i = \frac{r_i' - \operatorname{median}(r')}{\max(1.4826 \times \text{MAD},\; \sigma_{\min})}$$

---

## 7. CUSUM for Slow Drift Detection

### 7.1 Motivation

A z-score detects **instantaneous** spikes. A slowly developing fault — bearing wear, gradual insulation breakdown — may produce a sustained 1σ shift that never exceeds a spike threshold. The **Cumulative Sum** (CUSUM) algorithm accumulates small deviations over time.

### 7.2 One-Sided Upper CUSUM

For each point $i$, maintain a running statistic $S_i^+$:

$$S_i^{+}(t) = \max\!\left(0,\; S_i^{+}(t-1) + z_i(t) - k\right)$$

where:

- $k$ is the **allowance** (slack) parameter. It defines the minimum shift worth detecting. With $k = 0.5$, the CUSUM ignores normal noise centred at zero and only accumulates when $z_i > 0.5$.
- An alarm is raised when $S_i^{+}(t) \geq h$, the **decision interval** (threshold).

### 7.3 Parameter Selection

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| $k$ | 0.5 | Detects a sustained shift of 1σ. Smaller values catch smaller shifts but increase false alarms. |
| $h$ | 5.0 | With a 1σ sustained shift, the expected run length to detection is ~10 samples. At a 10 s sample interval, this is ~100 s — fast enough for thermal faults, slow enough to ignore transients. |

### 7.4 Detection Speed

Under a sustained shift of magnitude $\delta$ (in σ units), the expected number of samples to alarm is approximately:

$$N_{\text{alarm}} \approx \frac{h}{\delta - k}$$

For $\delta = 1.0$, $k = 0.5$, $h = 5.0$:

$$N_{\text{alarm}} \approx \frac{5.0}{1.0 - 0.5} = 10 \text{ samples}$$

### 7.5 Reset

After an alarm, $S_i^+$ is reset to zero. A lower-sided CUSUM $S_i^-$ can be maintained symmetrically for detecting abnormal cooling.

---

## 8. Two-Phase Learning

### 8.1 Phase 1: Offset Learning (Commissioning)

During initial deployment or after a sensor replacement:

1. The system runs under **known-good conditions** (no faults, normal load).
2. For each point $i$, peer-subtracted residuals $r_i$ are collected over a learning window of $L$ samples.
3. The per-point offset is estimated:

$$\hat{c}_i = \operatorname{median}(r_i^{(1)}, \ldots, r_i^{(L)})$$

4. The median is preferred over the mean for robustness against transient load variations during commissioning.

### 8.2 Phase 2: Freeze and Monitor

Once offsets are learned:

1. Offsets are **frozen** — they do not update during normal operation.
2. If offsets were allowed to adapt continuously, a slow-developing fault would be absorbed into the offset and become invisible.
3. The frozen offset acts as a reference against which all future measurements are compared.

### 8.3 Re-Learning

Offsets must be re-learned when:

- A sensor is physically moved or replaced.
- The monitored surface is repainted, cleaned, or mechanically altered.
- A known repair is completed and the system is confirmed healthy.

Re-learning is an explicit operator action, never automatic.

---

## 9. Cooldown Time-Constant (τ) Estimation

### 9.1 Thermal Model

When a heat source is removed (motor stops, VFD trips), the temperature rise decays exponentially:

$$\Delta T(t) = \Delta T_0 \, e^{-t/\tau}$$

where $\tau$ is the thermal time constant of the monitored component. Taking the logarithm:

$$\ln(\Delta T(t)) = \ln(\Delta T_0) - \frac{t}{\tau}$$

This is a **linear function of time** in log-space, with slope $m = -1/\tau$.

### 9.2 Key Property: Emissivity Invariance of Slope

The sensor reports $\Delta T_{\text{apparent}} = g \cdot \Delta T_{\text{true}}$. In log-space:

$$\ln(\Delta T_{\text{apparent}}(t)) = \ln(g) + \ln(\Delta T_0) - \frac{t}{\tau}$$

The emissivity factor $\ln(g)$ shifts the **intercept** but not the **slope**. Therefore:

$$\hat{\tau} = -\frac{1}{\hat{m}}$$

is independent of emissivity. This makes $\tau$ a robust, calibration-free diagnostic parameter.

### 9.3 Fitting Procedure

Perform ordinary least-squares linear regression on $(t_j, \ln(\Delta T_{\text{apparent},\, j}))$ pairs collected during a cooldown event:

$$\hat{m} = \frac{\sum_j (t_j - \bar{t})(\ln \Delta T_j - \overline{\ln \Delta T})}{\sum_j (t_j - \bar{t})^2}$$

$$\hat{\tau} = -\frac{1}{\hat{m}}$$

### 9.4 Quality Guards

Not every temperature decline is a valid cooldown event. The following guards ensure that $\hat{\tau}$ is estimated only from reliable data:

| Guard | Threshold | Rationale |
|-------|-----------|-----------|
| Minimum samples | $\geq 8$ | Regression on fewer points has excessive variance. |
| Minimum time span | $\geq 30$ s | A 30 s window ensures the decay is thermally meaningful, not sensor noise. |
| Minimum log decay | $\geq 0.15$ | Ensures the signal-to-noise ratio is adequate. A log decay of 0.15 corresponds to a ~14% drop in temperature rise. |
| Negative slope | $\hat{m} < 0$ | A positive slope means the surface is heating, not cooling. Reject. |
| Gap reset | $> 60$ s between consecutive samples | If a measurement gap exceeds 60 s (sensor offline, I²C error), discard the accumulated buffer and restart. The exponential model assumes continuous observation. |

### 9.5 Diagnostic Use

A sudden change in $\hat{\tau}$ for a motor indicates altered thermal mass or convection:

- **Increased $\tau$**: blocked ventilation, clogged filters, or insulation degradation (heat dissipates more slowly).
- **Decreased $\tau$**: improved cooling (e.g., after maintenance) or reduced thermal mass.

Trending $\hat{\tau}$ over weeks provides early warning of mechanical degradation.

---

## 10. Verdicts and Degraded Modes

### 10.1 Verdict Hierarchy

The system produces a per-point verdict at each sample interval:

| Verdict | Condition | Meaning |
|---------|-----------|---------|
| `OK` | $\|z_i\| < z_{\text{warn}}$ and $S_i^+ < h$ | Normal operation. |
| `WATCH` | $z_{\text{warn}} \leq \|z_i\| < z_{\text{alarm}}$ | Elevated asymmetry. Log and alert operator. |
| `ALARM` | $\|z_i\| \geq z_{\text{alarm}}$ or $S_i^+ \geq h$ | Significant asymmetry or sustained drift. Immediate action required. |
| `LEARNING` | Offset learning in progress | No verdicts issued; collecting baseline data. |
| `STALE` | Sensor read failure or timeout | Point excluded from peer group; verdict suspended. |

Typical thresholds: $z_{\text{warn}} = 3.0$, $z_{\text{alarm}} = 5.0$.

### 10.2 Degraded Modes

The algorithm degrades gracefully as sensors fail:

| Healthy Sensors | Peer Group Size | Behaviour |
|-----------------|-----------------|-----------|
| $n \geq 3$ | Full | Normal differential detection. MAD is reliable. |
| $n = 2$ | Pair | Peer subtraction still works (median = mean of two). MAD degenerates to $1.4826 \times |r_1 - r_2|/2$. Sensitivity is reduced. |
| $n = 1$ | None | Peer subtraction is impossible. Fall back to absolute-threshold monitoring on log-rise with widened thresholds. |
| $n = 0$ | None | System is blind. Raise a hardware fault. |

### 10.3 Quorum Rules

- A minimum of 3 healthy sensors is required for full confidence verdicts.
- With 2 sensors, verdicts are annotated as `DEGRADED`.
- With 1 sensor, only gross absolute anomalies are flagged (high false-alarm risk).

---

## 11. Near-Ambient Handling

### 11.1 The Problem

When a monitored component is near ambient temperature (e.g., motor at standstill), the temperature rise $\Delta T$ approaches zero. In log-space:

$$\lim_{\Delta T \to 0^+} \ln(\Delta T) = -\infty$$

The log-transform becomes numerically unstable. Sensor quantisation noise dominates, and tiny absolute differences produce enormous log-space residuals, triggering false alarms.

### 11.2 The Floor

A minimum rise floor is enforced:

$$\Delta T_{\text{eff}} = \max(\Delta T_{\text{apparent}},\; \text{MIN\_RISE\_K})$$

with $\text{MIN\_RISE\_K} = 1.5\;\text{K}$.

### 11.3 Rationale for 1.5 K

- The MLX90614 has a noise floor of ~0.5 K and a resolution of 0.02 K.
- At $\Delta T = 1.5$ K, the signal-to-noise ratio is ~3:1, sufficient for meaningful comparison.
- Below 1.5 K, emissivity-scaled differences are smaller than sensor noise — the differential signal is not physically meaningful.

### 11.4 Behaviour

When $\Delta T < \text{MIN\_RISE\_K}$ for **all** peers, the system enters a **near-ambient hold** state:

- Z-scores are clamped to zero.
- CUSUM accumulators are frozen (not reset — a pre-existing accumulation is preserved).
- Verdicts are held at `OK` or `STALE` as appropriate.
- Cooldown $\tau$ estimation is suppressed (insufficient signal).

When any peer exceeds the floor, normal processing resumes immediately.

---

## Summary of the Pipeline

```
   Raw IR reading (T_obj)
         │
         ▼
   Subtract T_amb  →  ΔT_apparent
         │
         ▼
   Floor at MIN_RISE_K (1.5 K)
         │
         ▼
   ln(ΔT_eff)  →  x_i
         │
         ▼
   Subtract peer median  →  r_i = x_i − median(x)
         │
         ▼
   Subtract learned offset  →  r_i' = r_i − ĉ_i
         │
         ▼
   Robust z-score  →  z_i = r_i' / max(1.4826·MAD, σ_min)
         │
         ├──→  Instantaneous verdict (|z| thresholds)
         │
         └──→  CUSUM accumulator  →  Drift verdict (S⁺ ≥ h)
```

Each stage removes a specific nuisance factor. What remains at the end is the pure asymmetry signal — the one thing that matters for fault detection.
