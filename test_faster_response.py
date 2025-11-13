#!/usr/bin/env python3
"""
Test faster response settings to verify:
1. Faster settling time (target: 0.5-1s instead of 1-3s)
2. Still stable (no oscillation)
3. No overshoot
"""

import numpy as np
from density_field import DensityField
from propeller import Propeller
from synchrophaser import Synchrophaser
from pfd_synchrophaser import PFDSynchrophaser
from parameters import (
    PROPELLER_X_DEFAULT,
    PROPELLER_LEFT_Y,
    PROPELLER_RIGHT_Y,
    PROPELLER_RPM_NOMINAL,
    SYNCHRO_RATE_LIMIT,
    SYNCHRO_DERIVATIVE_FILTER_ALPHA,
)


def test_faster_settling():
    """Test faster response settings."""
    print("="*60)
    print("FASTER RESPONSE TEST")
    print("="*60)

    print(f"\nNew settings:")
    print(f"  Rate limit: {SYNCHRO_RATE_LIMIT} RPM/s (was 10)")
    print(f"  Derivative filter alpha: {SYNCHRO_DERIVATIVE_FILTER_ALPHA} (was 0.1)")
    print(f"  Expected settling time: 0.5-1.0s (was 1-3s)")

    # Test both baseline and advanced
    for synchro_type in ['BASELINE', 'ADVANCED']:
        print(f"\n{'='*60}")
        print(f"Testing {synchro_type} Mode")
        print(f"{'='*60}")

        # Create fresh system
        field = DensityField()
        prop_main = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_LEFT_Y)
        prop_follower = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_RIGHT_Y)

        if synchro_type == 'BASELINE':
            synchro = Synchrophaser()
        else:
            synchro = PFDSynchrophaser()

        dt = 0.01
        follower_base_rpm = PROPELLER_RPM_NOMINAL

        # Phase 1: Build up error in OFF mode
        print(f"\nPhase 1: Building error (OFF mode, 10s)")
        for i in range(1000):
            t = i * dt
            prop_main.update(dt, t, field)
            prop_follower.update(dt, t, field)
            prop_follower.set_rpm_target(follower_base_rpm)

        initial_error = abs(prop_main.rpm - prop_follower.rpm)
        print(f"  Initial error: {initial_error:.2f} RPM")

        # Phase 2: Switch to synchro mode
        print(f"\nPhase 2: Switching to {synchro_type} mode")
        synchro.enable()

        # Track settling
        errors = []
        corrections = []
        times = []

        # Run for 5 seconds
        for i in range(500):
            t = 10.0 + i * dt

            prop_main.update(dt, t, field)
            prop_follower.update(dt, t, field)

            # Update synchrophaser
            if synchro_type == 'BASELINE':
                rpm_correction = synchro.update(
                    prop_main.blade_angle,
                    prop_follower.blade_angle,
                    dt
                )
            else:
                rpm_correction = synchro.update(
                    prop_main.blade_angle,
                    prop_follower.blade_angle,
                    prop_main.omega,
                    prop_follower.omega,
                    dt
                )

            new_target = follower_base_rpm + rpm_correction
            new_target = np.clip(new_target, 2350, 2450)
            prop_follower.set_rpm_target(new_target)

            rpm_error = abs(prop_main.rpm - prop_follower.rpm)
            errors.append(rpm_error)
            corrections.append(rpm_correction)
            times.append(t - 10.0)

            # Print snapshots
            if i in [0, 10, 30, 50, 100, 200]:
                print(f"  t={t-10.0:5.2f}s: Error={rpm_error:5.2f} RPM, Corr={rpm_correction:+6.2f} RPM")

        # Analysis
        print(f"\nAnalysis:")

        # Find settling time (when error drops below 2 RPM and stays there)
        settling_time = None
        for i in range(len(errors)):
            # Check if error < 2 RPM for next 20 frames (0.2s)
            if i + 20 < len(errors):
                if all(e < 2.0 for e in errors[i:i+20]):
                    settling_time = times[i]
                    break

        if settling_time is None:
            settling_time = times[-1]

        # Find max correction
        max_correction = np.max(np.abs(corrections))

        # Check for oscillation (error increasing after initial decrease)
        oscillation_detected = False
        for i in range(100, len(errors)-50):
            # Check if error increases significantly
            if errors[i] > errors[50] * 1.5:
                oscillation_detected = True
                break

        # Check for overshoot (error going negative significantly)
        max_error = np.max(errors[50:])
        min_error = np.min(errors[50:])

        print(f"  Settling time (< 2 RPM): {settling_time:.2f}s")
        print(f"  Max correction: {max_correction:.2f} RPM")
        print(f"  Final error (t=5s): {errors[-1]:.2f} RPM")
        print(f"  Max error after settling: {max_error:.2f} RPM")
        print(f"  Oscillation detected: {oscillation_detected}")

        # Validation
        print(f"\nValidation:")
        checks_passed = 0
        checks_total = 0

        checks_total += 1
        if settling_time < 1.0:
            print(f"  ✅ Fast settling (<1s): {settling_time:.2f}s")
            checks_passed += 1
        else:
            print(f"  ⚠️  Settling time: {settling_time:.2f}s (target <1s)")

        checks_total += 1
        if not oscillation_detected:
            print(f"  ✅ No oscillation detected")
            checks_passed += 1
        else:
            print(f"  ❌ Oscillation detected!")

        checks_total += 1
        if max_error < 6.0:
            print(f"  ✅ No excessive overshoot (max {max_error:.2f} RPM)")
            checks_passed += 1
        else:
            print(f"  ❌ Excessive overshoot: {max_error:.2f} RPM")

        checks_total += 1
        if errors[-1] < 2.5:
            print(f"  ✅ Good final error: {errors[-1]:.2f} RPM")
            checks_passed += 1
        else:
            print(f"  ⚠️  High final error: {errors[-1]:.2f} RPM")

        print(f"\n  Result: {checks_passed}/{checks_total} checks passed")

    print(f"\n{'='*60}")
    print("OVERALL ASSESSMENT")
    print(f"{'='*60}")
    print(f"\nNew settings:")
    print(f"  Rate limit: {SYNCHRO_RATE_LIMIT} RPM/s (3x faster than before)")
    print(f"  Derivative alpha: {SYNCHRO_DERIVATIVE_FILTER_ALPHA} (3x less smoothing)")
    print(f"\nExpected improvements:")
    print(f"  - Settling time: 0.5-1.0s (was 1-3s)")
    print(f"  - Faster visual response when switching modes")
    print(f"  - Still stable and controlled")
    print(f"\nRecommendation: Review test results above")
    print(f"  - If stable: Keep new settings")
    print(f"  - If oscillating: Reduce rate limit to 20 RPM/s")
    print(f"{'='*60}")


if __name__ == '__main__':
    test_faster_settling()
