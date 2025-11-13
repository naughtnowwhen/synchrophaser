# Anti-Overshoot Fix: Stable Synchrophaser Control

## Date: 2025-11-12

## Problem Identified by User

**Visual evidence:** Synchrophaser ON caused MORE oscillation than OFF
- Blue line (follower) jumping wildly
- Overshooting red line (main) repeatedly
- Chaotic, unstable behavior
- Test showed success but real-time was broken

**Root causes:**
1. **Gains too aggressive** - K_P=15, K_I=2, K_D=3 caused overcorrection
2. **Derivative amplifies noise** - Raw phase measurements are noisy, D-term made it worse
3. **No rate limiting** - Corrections could jump ±15 RPM instantly
4. **No deadband** - Correcting tiny errors caused jitter
5. **Phase scale too high** - 50 RPM/radian was too sensitive

---

## Solutions Implemented

### 1. Dramatically Reduced Gains

**File:** `parameters.py`

```python
# BEFORE (too aggressive):
SYNCHRO_K_P = 15.0
SYNCHRO_K_I = 2.0
SYNCHRO_K_D = 3.0
SYNCHRO_PHASE_SCALE = 50.0

# AFTER (conservative):
SYNCHRO_K_P = 1.0   # 93% reduction!
SYNCHRO_K_I = 0.1   # 95% reduction!
SYNCHRO_K_D = 0.5   # 83% reduction!
SYNCHRO_PHASE_SCALE = 30.0  # 40% reduction
```

**Why:** Slower, gentler corrections prevent overshoot and oscillation

---

### 2. Derivative Low-Pass Filter

**New parameter:**
```python
SYNCHRO_DERIVATIVE_FILTER_ALPHA = 0.1  # 90% smoothing
```

**Implementation in synchrophaser.py:218-232:**
```python
# Compute raw derivative (noisy!)
raw_derivative = (self.phase_error - self.previous_phase_error) / dt

# Apply exponential moving average filter
# filtered = alpha * raw + (1-alpha) * previous
self.filtered_derivative = (
    self.derivative_filter_alpha * raw_derivative +
    (1.0 - self.derivative_filter_alpha) * self.filtered_derivative
)

# Use FILTERED derivative (smooth!)
self.derivative_term = self.k_d * self.filtered_derivative
```

**Effect:**
- Alpha=0.1 means 90% of previous value + 10% of new measurement
- Smooths out noise over ~10 timesteps
- Prevents derivative kick from sudden changes

**Analogy:** Like using a moving average instead of instantaneous speed in your car's cruise control

---

### 3. Deadband for Small Errors

**New parameter:**
```python
SYNCHRO_DEADBAND = 0.01  # radians (~0.57°)
```

**Implementation in synchrophaser.py:192-199:**
```python
# DEADBAND: Ignore very small errors to reduce jitter
if abs(raw_phase_error) < self.deadband:
    # Error is tiny - don't correct, let integrator decay slightly
    self.phase_error = 0.0
    # Slowly decay integrator toward zero when in deadband
    self.integrator *= 0.99
else:
    self.phase_error = raw_phase_error
```

**Effect:**
- Errors below 0.57° are ignored
- Prevents "hunting" around the setpoint
- Reduces unnecessary corrections that cause jitter
- Integrator slowly decays to prevent buildup

**Real-world analogy:** Thermostat doesn't turn on/off for 0.1° changes

---

### 4. Rate Limiting on Corrections

**New parameter:**
```python
SYNCHRO_RATE_LIMIT = 10.0  # RPM/sec max change
```

**Implementation in synchrophaser.py:243-250:**
```python
# RATE LIMITING: Prevent sudden jumps in correction
if dt > 0:
    max_change = self.rate_limit * dt  # Max change per timestep
    correction_delta = desired_rpm_correction - self.previous_rpm_correction
    correction_delta = np.clip(correction_delta, -max_change, max_change)
    self.rpm_correction = self.previous_rpm_correction + correction_delta
```

**Effect:**
- At 100Hz update rate (dt=0.01s), max change = 0.1 RPM per step
- Smooths out sudden jumps
- Takes ~1.5 seconds to ramp from 0 to 15 RPM correction
- Prevents shock loads on governor

**Real-world analogy:** Acceleration limiter in electric vehicles

---

## Performance Comparison

### Before Anti-Overshoot Features

**Visual:** Wild oscillations, blue line jumping around red
**Test results:**
- Claimed 97.9% improvement
- But real-time showed instability
- User correctly identified it wasn't working

---

### After Anti-Overshoot Features

**Test results (30-second runs):**
```
Synchro OFF:
  Mean RPM error: 3.41 RPM
  Max RPM error:  12.08 RPM

Synchro ON:
  Mean RPM error: 1.29 RPM  (62% improvement)
  Max RPM error:  5.58 RPM

Corrections bounded: -6.5 to +9.9 RPM (smooth, no jumps)
```

**Expected visual behavior:**
- Smooth tracking between red and blue lines
- No rapid oscillations
- Gradual corrections, not sudden jumps
- Both lines stay close (~1 RPM typical)

---

## Technical Details

### Anti-Overshoot Feature Summary

| Feature | Parameter | Effect | Analogy |
|---------|-----------|--------|---------|
| **Low gains** | K_P=1.0, K_I=0.1, K_D=0.5 | Gentle corrections | Driving carefully, not jerking wheel |
| **Derivative filter** | Alpha=0.1 (90% smoothing) | Reduces noise amplification | Moving average vs instant speed |
| **Deadband** | 0.01 rad (~0.6°) | Ignores tiny errors | Thermostat tolerance zone |
| **Rate limiting** | 10 RPM/sec | Prevents sudden jumps | Acceleration limiter |
| **Phase scale** | 30 RPM/radian | Reduces sensitivity | Lower steering ratio |

---

### Control Loop Flow

```
1. Measure blade angles
   ↓
2. Compute phase error (wrapped to ±π)
   ↓
3. Apply DEADBAND filter (ignore if < 0.57°)
   ↓
4. Proportional term: K_P * error
   ↓
5. Integral term: K_I * ∫error dt (with anti-windup)
   ↓
6. Derivative term: K_D * FILTERED(d(error)/dt)
   ↓
7. Combine PID terms
   ↓
8. Convert to RPM (phase * 30)
   ↓
9. Apply RATE LIMITER (max 10 RPM/s change)
   ↓
10. Apply final safety limits (±15 RPM)
   ↓
11. Send to follower governor
```

---

## What Each Feature Prevents

### 1. Low Gains Prevent:
- Overshoot (going past target)
- Oscillation (back-and-forth hunting)
- Aggressive corrections that destabilize

### 2. Derivative Filter Prevents:
- Noise amplification (D-term magnifying measurement errors)
- High-frequency oscillations
- "Derivative kick" from sudden changes

### 3. Deadband Prevents:
- Hunting (constant tiny corrections)
- Jitter (visual shake in display)
- Unnecessary governor activity
- Integrator buildup from noise

### 4. Rate Limiting Prevents:
- Sudden jumps in correction
- Shock loads on governor
- Visual "teleporting" in graphs
- Unstable transients

---

## Tuning Philosophy

### Conservative Approach

**Old thinking:** "Phase error is important, use high gains to correct quickly!"
- Result: Overshoot, oscillation, instability

**New thinking:** "Slow, smooth corrections that converge without overshoot"
- Result: Stable, gradual synchronization

**Key insight:** Better to track with 1-2 RPM error smoothly than to oscillate wildly trying for perfect lock.

---

### Why This Works

**From control theory:**
1. **Proportional** - Provides basic response (K_P=1.0 is gentle)
2. **Integral** - Eliminates steady-state error slowly (K_I=0.1 = slow accumulation)
3. **Derivative** - Dampens oscillations if filtered properly (K_D=0.5 with heavy filtering)

**Multiple layers of protection:**
- Deadband stops corrections before they start (if error is tiny)
- Low gains make corrections gentle (if error is significant)
- Derivative filter smooths response (prevents noise amplification)
- Rate limiter prevents sudden changes (physical realism)
- Final clipping provides hard safety limit

---

## Testing Results

### Automated Test (test_synchrophaser.py)

```
============================================================
TEST 2: Synchrophaser ON (30 seconds)
============================================================
t= 0.0s: Main= 2400.6, Follower= 2400.3, Diff=0.4 RPM, Corr=+0.0
t= 5.0s: Main= 2395.2, Follower= 2394.7, Diff=0.5 RPM, Corr=-2.7
t=10.0s: Main= 2404.1, Follower= 2404.7, Diff=0.6 RPM, Corr=-1.4
t=15.0s: Main= 2402.4, Follower= 2402.6, Diff=0.2 RPM, Corr=-6.4
t=20.0s: Main= 2405.7, Follower= 2406.2, Diff=0.5 RPM, Corr=+9.9
t=25.0s: Main= 2398.4, Follower= 2398.5, Diff=0.1 RPM, Corr=-6.5

Mean RPM error: 1.29 RPM (was 3.41 OFF)
Max RPM error:  5.58 RPM (was 12.08 OFF)
Improvement: 62.2% reduction
```

**Observations:**
- Corrections bounded: -6.5 to +9.9 RPM ✓
- No wild swings or sudden jumps ✓
- Typical tracking: 0.2-0.6 RPM ✓
- Max error 5.58 RPM (transient, not sustained) ✓

---

## Expected Visual Behavior

### When Synchrophaser OFF:
- Red and blue lines diverge and wander
- Typical separation: 2-6 RPM
- Max separation: ~12 RPM
- Lines cross randomly

### When Synchrophaser ON (NEW):
- Red and blue lines track closely
- Smooth, gradual convergence (not instant)
- Typical separation: 0.5-1.5 RPM
- No wild oscillations
- No sudden jumps
- Both lines move together smoothly

**If you still see oscillations:**
- Gains may need to be even lower
- Derivative filter alpha may need reduction (try 0.05 for more smoothing)
- Rate limit may need tightening (try 5.0 RPM/s)

---

## Files Modified

1. **parameters.py** (lines 100-114)
   - Reduced K_P, K_I, K_D dramatically
   - Reduced phase scale
   - Added derivative filter alpha
   - Added deadband
   - Added rate limit

2. **synchrophaser.py**
   - Imported new parameters (lines 17-28)
   - Added state variables (lines 93-94)
   - Updated enable/disable (lines 105-123)
   - Implemented deadband (lines 192-199)
   - Implemented derivative filter (lines 218-232)
   - Implemented rate limiting (lines 243-250)

---

## Usage

### Test Stability
```bash
python3 test_synchrophaser.py
```

Should show:
- ~60-70% improvement
- Mean error ~1-2 RPM when ON
- Corrections bounded to ±10 RPM range
- No negative improvement (making things worse)

### Visual Test
```bash
python3 main.py
```

Expected behavior:
1. **Start with synchro OFF:** Lines diverge naturally (2-6 RPM separation)
2. **Toggle synchro ON:** Lines gradually converge over 2-3 seconds
3. **Steady state:** Lines track closely (~0.5-1 RPM separation)
4. **During disturbances:** Smooth corrections, no jumping

---

## Further Tuning (If Needed)

### If Still Oscillating:
1. **Reduce gains further:**
   ```python
   SYNCHRO_K_P = 0.5  # Half current value
   SYNCHRO_K_I = 0.05  # Half current value
   SYNCHRO_K_D = 0.25  # Half current value
   ```

2. **Increase derivative filtering:**
   ```python
   SYNCHRO_DERIVATIVE_FILTER_ALPHA = 0.05  # More smoothing
   ```

3. **Tighten rate limit:**
   ```python
   SYNCHRO_RATE_LIMIT = 5.0  # Slower changes
   ```

### If Too Slow to Converge:
1. **Slightly increase K_P:**
   ```python
   SYNCHRO_K_P = 1.5  # A bit more aggressive
   ```

2. **Widen deadband slightly:**
   ```python
   SYNCHRO_DEADBAND = 0.02  # ~1.1° tolerance
   ```

---

## Key Lessons

### 1. Test Results ≠ Real Performance
- Scripted tests can pass while real-time fails
- Visual inspection is critical
- User feedback caught what automated tests missed

### 2. Derivative is Double-Edged
- D-term can dampen oscillations (good)
- But amplifies measurement noise (bad)
- **MUST be filtered** for noisy signals
- Low-pass filter is essential

### 3. Multiple Safety Layers
- Don't rely on a single protection mechanism
- Deadband + low gains + rate limiting + clipping = robust
- Each layer catches different failure modes

### 4. Conservative Tuning Wins
- Better to be slow and stable than fast and chaotic
- 60% improvement smoothly > 95% improvement with oscillation
- Users prefer predictable behavior

---

## Real-World Comparison

**Modern aircraft synchrophasers also use:**
- Low-pass filtered derivative (Butterworth or moving average)
- Deadband or hysteresis to prevent hunting
- Rate limiting to protect mechanical components
- Conservative gains tuned for stability over speed

**Our simulation now matches these practices!**

---

## Status

**Anti-Overshoot Fix: COMPLETE ✓**

All features implemented:
- ✅ Reduced gains (93-95% lower)
- ✅ Derivative low-pass filter (90% smoothing)
- ✅ Deadband (0.57° tolerance)
- ✅ Rate limiting (10 RPM/s max)
- ✅ Reduced phase scale (40% lower)

**Test results:**
- ✅ 62.2% improvement
- ✅ Corrections bounded and smooth
- ✅ No oscillation in test data
- ⏳ Visual confirmation pending (user to test)

**Ready for real-time testing!**

---

**Date:** 2025-11-12
**Test Status:** Automated tests pass, awaiting visual confirmation
**Next Step:** User runs `python3 main.py` to verify smooth behavior

---

## Quick Reference: What Changed

**Before:**
- K_P=15, K_I=2, K_D=3 → Wild oscillations
- Raw derivative → Noise amplification
- No deadband → Hunting/jitter
- No rate limiting → Sudden jumps
- Phase scale=50 → Too sensitive

**After:**
- K_P=1, K_I=0.1, K_D=0.5 → Gentle corrections
- Filtered derivative (alpha=0.1) → Smooth response
- Deadband (0.57°) → No hunting
- Rate limiting (10 RPM/s) → Smooth changes
- Phase scale=30 → Less sensitive

**Result:** Stable, smooth tracking instead of chaotic oscillation
