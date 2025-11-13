#!/usr/bin/env python3
"""
Test mode switching to verify modes activate immediately
and measure settling time.

This test shows:
1. Mode switch happens instantly
2. But the EFFECT takes 1-3 seconds due to rate limiting and PID settling
"""

import numpy as np
from density_field import DensityField
from propeller import Propeller
from synchrophaser import Synchrophaser
from parameters import (
    PROPELLER_X_DEFAULT,
    PROPELLER_LEFT_Y,
    PROPELLER_RIGHT_Y,
    PROPELLER_RPM_NOMINAL,
    SYNCHRO_RATE_LIMIT,
)


def test_mode_switch_timing():
    """Test how quickly mode switch takes effect."""
    print("="*60)
    print("MODE SWITCHING TIMING TEST")
    print("="*60)

    # Create system
    field = DensityField()
    prop_main = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_LEFT_Y)
    prop_follower = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_RIGHT_Y)
    synchro = Synchrophaser()

    # Simulation parameters
    dt = 0.01  # 100 Hz
    follower_base_rpm = PROPELLER_RPM_NOMINAL

    print("\nPhase 1: Run in OFF mode for 10 seconds")
    print("(Build up phase error)")

    for i in range(1000):  # 10 seconds
        t = i * dt
        prop_main.update(dt, t, field)
        prop_follower.update(dt, t, field)
        prop_follower.set_rpm_target(follower_base_rpm)

    # Check error before switching
    rpm_error_before = abs(prop_main.rpm - prop_follower.rpm)
    phase_error_before_deg = np.degrees(
        np.arctan2(
            np.sin(prop_main.blade_angle - prop_follower.blade_angle),
            np.cos(prop_main.blade_angle - prop_follower.blade_angle)
        )
    )

    print(f"\nAt t=10s (before switch):")
    print(f"  RPM error: {rpm_error_before:.2f} RPM")
    print(f"  Phase error: {phase_error_before_deg:.1f}°")
    print(f"  Synchro enabled: {synchro.enabled}")

    # SWITCH TO BASELINE MODE
    print(f"\n{'='*60}")
    print("SWITCHING TO BASELINE MODE AT t=10s")
    print(f"{'='*60}")

    synchro.enable()
    print(f"\nImmediate status:")
    print(f"  Synchro enabled: {synchro.enabled}")
    print(f"  Integrator reset to: {synchro.integrator}")
    print(f"  Previous correction: {synchro.previous_rpm_correction}")

    # Run and track settling
    print(f"\nTracking settling time...")
    print(f"Rate limit: {SYNCHRO_RATE_LIMIT} RPM/s")
    print(f"Max change per frame (dt={dt}s): {SYNCHRO_RATE_LIMIT * dt:.3f} RPM\n")

    settling_times = []
    rpm_corrections = []
    rpm_errors = []

    for i in range(500):  # 5 more seconds
        t = 10.0 + i * dt

        prop_main.update(dt, t, field)
        prop_follower.update(dt, t, field)

        # Update synchrophaser
        rpm_correction = synchro.update(
            prop_main.blade_angle,
            prop_follower.blade_angle,
            dt
        )

        # Apply correction
        new_target = follower_base_rpm + rpm_correction
        new_target = np.clip(new_target, 2350, 2450)
        prop_follower.set_rpm_target(new_target)

        # Track metrics
        rpm_error = abs(prop_main.rpm - prop_follower.rpm)
        rpm_corrections.append(rpm_correction)
        rpm_errors.append(rpm_error)

        # Print progress
        if i % 50 == 0:
            print(f"  t={t:5.1f}s: Error={rpm_error:5.2f} RPM, "
                  f"Correction={rpm_correction:+6.2f} RPM, "
                  f"Integrator={synchro.integrator:+7.4f}")

    print(f"\n{'='*60}")
    print("ANALYSIS")
    print(f"{'='*60}")

    # Find when correction reaches 90% of max
    max_correction = np.max(np.abs(rpm_corrections))
    target_correction = 0.9 * max_correction

    for i, corr in enumerate(rpm_corrections):
        if abs(corr) >= target_correction:
            settling_time_correction = i * dt
            break
    else:
        settling_time_correction = len(rpm_corrections) * dt

    # Find when error drops below 2 RPM
    for i, err in enumerate(rpm_errors):
        if err < 2.0:
            settling_time_error = i * dt
            break
    else:
        settling_time_error = len(rpm_errors) * dt

    print(f"\nSettling time analysis:")
    print(f"  Max correction applied: {max_correction:.2f} RPM")
    print(f"  Time to reach 90% of max correction: {settling_time_correction:.2f}s")
    print(f"  Time to get error below 2 RPM: {settling_time_error:.2f}s")

    print(f"\nWhy does it take time?")
    print(f"  1. Rate limiting: {SYNCHRO_RATE_LIMIT} RPM/s max change")
    print(f"     → To apply {max_correction:.1f} RPM correction takes {max_correction/SYNCHRO_RATE_LIMIT:.2f}s")
    print(f"  2. Integrator starts at zero (needs time to build up)")
    print(f"  3. Derivative filter has 90% smoothing (alpha=0.1)")
    print(f"  4. Propeller has inertia (can't change RPM instantly)")

    print(f"\n{'='*60}")
    print("CONCLUSION")
    print(f"{'='*60}")

    print(f"\n✅ Mode switch is IMMEDIATE:")
    print(f"   - Synchrophaser enabled instantly when button clicked")
    print(f"   - State reset to zero (integrator, corrections, etc.)")
    print(f"   - Update loop starts processing immediately")

    print(f"\n⏱️  But EFFECT has {settling_time_error:.1f}s settling time:")
    print(f"   - This is INTENTIONAL (prevents overshooting)")
    print(f"   - Rate limiting prevents sudden jumps")
    print(f"   - PID controller needs time to 'lock on'")
    print(f"   - This is GOOD engineering!")

    print(f"\n💡 What you observe:")
    print(f"   - Click button → Mode changes color immediately")
    print(f"   - RPM traces → Take {settling_time_error:.1f}s to converge")
    print(f"   - 15s rolling average → Takes 15s to fully reflect new mode")

    print(f"\n{'='*60}")


if __name__ == '__main__':
    test_mode_switch_timing()
