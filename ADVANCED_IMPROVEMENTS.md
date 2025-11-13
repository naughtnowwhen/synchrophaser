# Advanced Synchrophaser Improvements - Legitimate Techniques

## Goal
Improve synchronization quality beyond current 62% improvement (1.29 RPM error) using legitimate control theory that could be deployed in real aircraft.

**Constraints:**
- ✅ No cheating (no direct speed copying, forced angles, etc.)
- ✅ Must work through governor dynamics
- ✅ Must be physically realizable
- ✅ Safety-critical quality (real aircraft deployment)
- ✅ All techniques from published research/industry practice

---

## Current Performance (Baseline)

**Working Sync Mode:**
- Algorithm: PID with filtered derivative, deadband, rate limiting
- Mean error: 1.29 RPM (62% improvement over OFF)
- Max error: 5.58 RPM
- Corrections: -6.5 to +9.9 RPM
- Status: Stable, proven

**This is our safety baseline - never remove!**

---

## Proposed Advanced Techniques

All techniques below are from aerospace/industrial control literature and are **completely legitimate**.

---

### 1. Feedforward from Main Propeller ⭐ HIGHEST IMPACT

**Concept:**
The main propeller encounters atmospheric disturbances first. Use its RPM variations as an early warning signal for the follower.

**Why it's legitimate:**
- Main propeller acts as a "sensor" for upcoming air density
- Follower is slightly behind in the flow
- Real aircraft could implement this
- Used in industrial cascaded control systems

**Implementation:**
```python
# Measure main propeller's RPM deviation from nominal
main_rpm_error = prop_main.rpm - NOMINAL_RPM

# Feedforward term: anticipate follower will see similar disturbance
feedforward_term = K_FF * main_rpm_error

# Total correction = PID + feedforward
rpm_correction = pid_output + feedforward_term
```

**Expected improvement:**
- 10-20% additional error reduction
- Proactive vs. reactive control
- Faster disturbance rejection

**Safety:**
- Feedforward gain K_FF should be conservative (0.3-0.5)
- Can't cause instability (feedforward doesn't affect feedback loop stability)
- If main sensor fails, falls back to PID only

---

### 2. Kalman Filter for Phase Estimation ⭐ HIGH IMPACT

**Concept:**
Instead of using raw blade angle measurements (noisy), use a Kalman filter to estimate true phase optimally.

**Why it's legitimate:**
- Blade position sensors have noise (vibration, quantization)
- Kalman filter is optimal estimator for noisy measurements
- Used in aircraft navigation, spacecraft, automotive
- Standard in modern control systems

**Implementation:**
```python
class PhaseKalmanFilter:
    """
    Optimal estimator for blade phase from noisy measurements.

    State: [phase, phase_rate]
    Measurement: raw_phase_angle
    """
    def __init__(self):
        self.phase_est = 0.0
        self.phase_rate_est = 0.0
        self.P = np.eye(2)  # Covariance matrix

    def update(self, measured_phase, dt):
        # Prediction step
        phase_pred = self.phase_est + self.phase_rate_est * dt

        # Update with measurement
        innovation = measured_phase - phase_pred
        # ... Kalman gain computation ...

        return self.phase_est  # Filtered estimate
```

**Expected improvement:**
- Smoother phase tracking
- Better noise rejection than simple filtering
- More accurate error measurement

**Safety:**
- Well-established algorithm (Apollo program, F-16, etc.)
- Graceful degradation if parameters mistuned
- Can validate with ground testing

---

### 3. Adaptive PID Gains ⭐ MEDIUM-HIGH IMPACT

**Concept:**
Automatically adjust PID gains based on operating conditions (smooth air vs. turbulence).

**Why it's legitimate:**
- Fixed gains are compromise between performance and stability
- Can do better by adapting to conditions
- Real aircraft have "gain scheduling" (speed-dependent gains)
- Modern automotive cruise control uses adaptive gains

**Implementation:**
```python
# Monitor error statistics over sliding window
error_variance = np.var(recent_phase_errors)

if error_variance < LOW_TURBULENCE_THRESHOLD:
    # Calm air - can use higher gains for tighter tracking
    K_P = 1.5  # vs. baseline 1.0
    K_I = 0.15
    K_D = 0.7
else:
    # Turbulent air - use conservative gains
    K_P = 0.8
    K_I = 0.05
    K_D = 0.3
```

**Expected improvement:**
- 10-15% better in calm air
- More robust in turbulence
- Self-tuning

**Safety:**
- Always stay within safe gain bounds
- Slow adaptation (don't change gains rapidly)
- Revert to conservative default if uncertain

---

### 4. Derivative on Measurement (Not Error) ⭐ MEDIUM IMPACT

**Concept:**
Current D-term uses d(error)/dt. Alternative: use d(follower_phase)/dt only.

**Why it's legitimate:**
- Avoids "derivative kick" when setpoint (main phase) changes suddenly
- Standard industrial practice (called "derivative on measurement")
- More stable, smoother control

**Implementation:**
```python
# Current (derivative on error):
derivative_term = K_D * (phase_error - previous_phase_error) / dt

# Alternative (derivative on measurement):
derivative_term = -K_D * (follower_phase - previous_follower_phase) / dt
# Negative sign: damping acts against follower's motion
```

**Expected improvement:**
- Smoother response to main propeller changes
- Less overshoot
- Better suited to tracking applications

**Safety:**
- Still provides damping
- More conservative than derivative on error
- Industry-proven technique

---

### 5. Bumpless Transfer on Enable ⭐ LOW-MEDIUM IMPACT

**Concept:**
When synchrophaser turns ON, initialize integrator and correction to minimize transient.

**Why it's legitimate:**
- Prevents sudden jump when enabling
- Smooth transition
- Standard in industrial controllers ("bumpless transfer")

**Implementation:**
```python
def enable(self):
    self.enabled = True

    # Initialize integrator to current steady-state error
    # (prevents sudden jump in I-term)
    current_phase_error = self.compute_phase_error(...)
    self.integrator = current_phase_error / self.k_i  # Pre-fill

    # Initialize previous correction to zero for smooth ramp-up
    self.previous_rpm_correction = 0.0
```

**Expected improvement:**
- Smoother enable transient
- Faster convergence (no overshoot on turn-on)
- Better user experience

**Safety:**
- Only affects turn-on transient
- Can't cause instability
- Easy to validate

---

### 6. Two-Degree-of-Freedom (2DOF) PID ⭐ LOW-MEDIUM IMPACT

**Concept:**
Separate tuning for setpoint tracking vs. disturbance rejection.

**Why it's legitimate:**
- Standard PID has one set of gains for both tasks
- Can optimize each separately with 2DOF
- Used in process control, motion control

**Implementation:**
```python
# Setpoint weighting on P and D terms
setpoint_weight_p = 0.5  # Reduce aggressive setpoint tracking
setpoint_weight_d = 0.0  # No derivative on setpoint (avoid kick)

# P-term
p_term = K_P * (setpoint_weight_p * setpoint - measurement)

# D-term (only on measurement, weighted)
d_term = -K_D * d(measurement)/dt
```

**Expected improvement:**
- Better tracking vs. disturbance trade-off
- More tuning flexibility
- 5-10% improvement possible

**Safety:**
- Reduces to standard PID with weights = 1.0
- Can tune conservatively
- Well-established technique

---

### 7. Smith Predictor (Advanced) ⭐ LOW IMPACT (complex)

**Concept:**
Explicitly model and compensate for governor response delay.

**Why it's legitimate:**
- Governor has ~0.1-0.5s lag
- Smith predictor compensates for known delays
- Used in process control (long pipe delays)

**Implementation:**
```python
# Model: follower RPM response has delay τ
# Smith predictor predicts RPM without delay
predicted_rpm = model(correction, tau=0)  # No delay model
measured_rpm = actual_follower.rpm  # Has delay

# Compute error on predicted state
error_compensated = main_rpm - predicted_rpm
```

**Expected improvement:**
- 5-10% better in theory
- Complex to tune
- Requires accurate delay model

**Safety:**
- Can make system unstable if delay misestimated
- Recommend NOT implementing unless critical
- Include only if extensive testing possible

---

## Recommended "Advanced" Mode

### Tier 1: High-Confidence, High-Impact (Implement These)

1. **Feedforward from Main** - Biggest bang for buck
2. **Kalman Filter** - Better estimation
3. **Adaptive Gains** - Self-tuning

### Tier 2: Medium-Confidence, Medium-Impact (Consider)

4. **Derivative on Measurement** - Industry standard
5. **Bumpless Transfer** - User experience

### Tier 3: Complex, Lower Priority (Later)

6. **2DOF PID** - Marginal benefit
7. **Smith Predictor** - High complexity, model-dependent

---

## Proposed "Advanced" Implementation

```python
class AdvancedSynchrophaser(Synchrophaser):
    """
    Enhanced synchrophaser with advanced control techniques.

    Improvements over baseline:
    1. Feedforward from main propeller
    2. Kalman filter for phase estimation
    3. Adaptive PID gains
    4. Derivative on measurement
    5. Bumpless transfer
    """

    def __init__(self, ...):
        super().__init__(...)

        # Feedforward
        self.k_ff = 0.4  # Feedforward gain (conservative)

        # Kalman filter for phase
        self.phase_kf = PhaseKalmanFilter(
            process_noise=0.01,  # rad²/s
            measurement_noise=0.02  # rad²
        )

        # Adaptive gains
        self.adaptive_enabled = True
        self.error_window = deque(maxlen=100)  # Sliding window

        # Derivative on measurement
        self.use_derivative_on_measurement = True
        self.previous_follower_phase = 0.0

    def update(self, blade_angle_main, blade_angle_follower,
               rpm_main, rpm_follower, dt):
        """
        Advanced control with feedforward, Kalman filtering, adaptation.
        """
        # 1. Kalman filter phase measurements
        filtered_main_phase = self.phase_kf_main.update(blade_angle_main, dt)
        filtered_follower_phase = self.phase_kf_follower.update(blade_angle_follower, dt)

        # 2. Compute phase error on filtered estimates
        phase_error = self.compute_phase_error(filtered_main_phase, filtered_follower_phase)

        # Apply deadband
        if abs(phase_error) < self.deadband:
            phase_error = 0.0

        # 3. Adaptive gains based on recent error variance
        if self.adaptive_enabled:
            self.adapt_gains()

        # 4. PID with derivative on measurement
        p_term = self.k_p * phase_error

        # Integral
        self.integrator += phase_error * dt
        self.integrator = np.clip(self.integrator, -0.5, 0.5)
        i_term = self.k_i * self.integrator

        # Derivative on measurement (not error)
        if self.use_derivative_on_measurement:
            phase_rate = (filtered_follower_phase - self.previous_follower_phase) / dt
            d_term = -self.k_d * phase_rate  # Negative: opposes motion
        else:
            # Standard derivative on error (with filtering)
            d_term = self.compute_filtered_derivative(phase_error, dt)

        # 5. Feedforward from main propeller
        main_rpm_deviation = rpm_main - self.nominal_rpm
        ff_term = self.k_ff * main_rpm_deviation

        # 6. Combine all terms
        pid_output = p_term + i_term + d_term
        rpm_correction = pid_output * self.phase_scale + ff_term

        # Rate limiting and clipping (same as baseline)
        rpm_correction = self.apply_rate_limit(rpm_correction, dt)
        rpm_correction = np.clip(rpm_correction, -15.0, 15.0)

        # Update state
        self.previous_follower_phase = filtered_follower_phase
        self.error_window.append(abs(phase_error))

        return rpm_correction

    def adapt_gains(self):
        """Adjust gains based on recent error statistics."""
        if len(self.error_window) < 50:
            return  # Not enough data

        error_variance = np.var(list(self.error_window))

        # Thresholds (tune experimentally)
        LOW_VARIANCE = 0.0002  # rad² (calm conditions)
        HIGH_VARIANCE = 0.002  # rad² (turbulent)

        if error_variance < LOW_VARIANCE:
            # Calm air - increase gains
            self.k_p = 1.5
            self.k_i = 0.15
            self.k_d = 0.7
        elif error_variance > HIGH_VARIANCE:
            # Turbulent - decrease gains
            self.k_p = 0.8
            self.k_i = 0.05
            self.k_d = 0.3
        else:
            # Medium - baseline gains
            self.k_p = 1.0
            self.k_i = 0.1
            self.k_d = 0.5
```

---

## Expected Performance: "Advanced" Mode

**Conservative estimate:**
- Mean error: 0.8-1.0 RPM (vs. 1.29 baseline)
- Max error: 3-4 RPM (vs. 5.58 baseline)
- Improvement: 70-75% over OFF (vs. 62% baseline)

**Optimistic (if conditions favorable):**
- Mean error: 0.5-0.7 RPM
- Max error: 2-3 RPM
- Improvement: 80-85% over OFF

**Still realistic:** Not 0.00 RPM (physics, noise, dynamics)

---

## Safety Considerations (Real Aircraft Deployment)

### Validation Requirements

1. **Ground Testing:**
   - Extensive testing in simulation
   - Verify stability under all conditions
   - Failure mode analysis

2. **Fallback to Baseline:**
   - If advanced mode shows instability
   - Automatic revert to proven baseline
   - Pilot can disable via switch

3. **Monitoring:**
   - Track phase error, corrections, gain values
   - Alert if excessive error or correction
   - Datalog for analysis

4. **Conservative Limits:**
   - All gains bounded to safe ranges
   - Correction limits enforced
   - Rate limiting always active

### Failure Modes

**If Kalman filter fails:**
- Revert to raw measurements
- Still functional (degraded performance)

**If feedforward misbehaves:**
- Disable feedforward term
- Falls back to feedback-only (baseline)

**If adaptation goes wrong:**
- Freeze gains at last good values
- Or revert to baseline fixed gains

**Critical:** Synchrophaser failure must not cause unsafe condition - propellers run independently at base RPM if all else fails.

---

## Testing Plan

### Phase 1: Simulation Validation
1. Implement advanced mode
2. Test against baseline in various conditions
3. Verify improvement and stability
4. Tune parameters

### Phase 2: Systematic Comparison
1. Run 60s OFF / 60s Baseline / 60s Advanced
2. Compare statistics
3. Ensure advanced doesn't regress

### Phase 3: Stress Testing
1. Extreme turbulence
2. Sudden enable/disable
3. Parameter variations
4. Edge cases

### Phase 4: Safety Analysis
1. Failure mode testing
2. Fallback validation
3. Performance bounds verification

---

## UI Design: Three-Mode Toggle

```
┌─────────────────────────────────────┐
│  Synchrophaser Mode:                │
│                                     │
│  ○ OFF                              │
│  ● BASELINE  (Current: Proven)      │
│  ○ ADVANCED  (Experimental)         │
│                                     │
│  Status: Active                     │
│  Mode: Baseline PID                 │
│  Error: 1.2 RPM                     │
└─────────────────────────────────────┘
```

**Three buttons:**
1. **OFF** - Propellers independent (for comparison)
2. **BASELINE** - Current proven PID (62% improvement)
3. **ADVANCED** - New techniques (targeting 75%+ improvement)

---

## Summary

All proposed techniques are:
✅ Legitimate control theory
✅ Used in real aerospace/industrial systems
✅ Work through governor dynamics (no cheating)
✅ Have safety fallbacks
✅ Suitable for real aircraft

**Recommended approach:**
1. Keep baseline mode as safety fallback
2. Implement Tier 1 features in advanced mode
3. Extensive testing and validation
4. Compare performance systematically

**Goal:** 70-80% improvement with advanced mode (vs. 62% baseline) while maintaining safety and stability.

---

**Ready to implement when you approve!**
