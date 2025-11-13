#!/usr/bin/env python3
"""
Test synchrophaser effectiveness with twin propellers.
"""

import numpy as np
from density_field import DensityField
from propeller import Propeller
from synchrophaser import Synchrophaser

def test_twin_propellers():
    """Test twin propellers with and without synchrophaser."""
    print("=" * 60)
    print("SYNCHROPHASER EFFECTIVENESS TEST")
    print("=" * 60)

    # Create components
    field = DensityField(wavelength=150.0, drift_velocity=50.0, seed=42)
    prop_main = Propeller(x=900, y=-60)  # Below centerline
    prop_follower = Propeller(x=900, y=60)  # Above centerline
    synchro = Synchrophaser()

    print(f"\nPropeller positions:")
    print(f"  Main:     ({prop_main.x:.0f}m, {prop_main.y:.0f}m)")
    print(f"  Follower: ({prop_follower.x:.0f}m, {prop_follower.y:.0f}m)")
    print(f"  Separation: {abs(prop_main.y - prop_follower.y):.0f}m")

    # Test WITHOUT synchrophaser (30 seconds)
    print(f"\n{'='*60}")
    print("TEST 1: Synchrophaser OFF (30 seconds)")
    print(f"{'='*60}")

    synchro.disable()
    dt = 0.01
    duration = 30.0

    rpm_errors_off = []
    phase_errors_off = []

    for i in range(int(duration / dt)):
        t = i * dt

        # Update propellers
        prop_main.update(dt, t, field)
        prop_follower.update(dt, t, field)

        # Update synchro (disabled, so no correction)
        synchro.update(prop_main.blade_angle, prop_follower.blade_angle, dt)

        # Collect metrics
        rpm_error = abs(prop_main.rpm - prop_follower.rpm)
        rpm_errors_off.append(rpm_error)
        phase_errors_off.append(abs(synchro.phase_error))

        if i % 500 == 0:  # Print every 5 seconds
            print(f"t={t:4.1f}s: Main={prop_main.rpm:7.1f}, "
                  f"Follower={prop_follower.rpm:7.1f}, "
                  f"Diff={rpm_error:.1f} RPM")

    # Statistics for OFF
    mean_rpm_error_off = np.mean(rpm_errors_off)
    max_rpm_error_off = np.max(rpm_errors_off)

    print(f"\nResults (OFF):")
    print(f"  Mean RPM error: {mean_rpm_error_off:.2f} RPM")
    print(f"  Max RPM error:  {max_rpm_error_off:.2f} RPM")

    # Reset propellers to initial state
    prop_main = Propeller(x=900, y=-60)
    prop_follower = Propeller(x=900, y=60)
    synchro = Synchrophaser()

    # Test WITH synchrophaser (30 seconds)
    print(f"\n{'='*60}")
    print("TEST 2: Synchrophaser ON (30 seconds)")
    print(f"{'='*60}")

    synchro.enable()

    rpm_errors_on = []
    phase_errors_on = []
    follower_base_rpm = prop_follower.rpm_nominal

    for i in range(int(duration / dt)):
        t = i * dt

        # Update propellers
        prop_main.update(dt, t, field)
        prop_follower.update(dt, t, field)

        # Update synchro and apply correction
        rpm_correction = synchro.update(prop_main.blade_angle, prop_follower.blade_angle, dt)
        new_target = follower_base_rpm + rpm_correction
        prop_follower.set_rpm_target(new_target)

        # Collect metrics
        rpm_error = abs(prop_main.rpm - prop_follower.rpm)
        rpm_errors_on.append(rpm_error)
        phase_errors_on.append(abs(synchro.phase_error))

        if i % 500 == 0:  # Print every 5 seconds
            print(f"t={t:4.1f}s: Main={prop_main.rpm:7.1f}, "
                  f"Follower={prop_follower.rpm:7.1f}, "
                  f"Diff={rpm_error:.1f} RPM, "
                  f"Corr={rpm_correction:+.1f}")

    # Statistics for ON
    mean_rpm_error_on = np.mean(rpm_errors_on)
    max_rpm_error_on = np.max(rpm_errors_on)

    print(f"\nResults (ON):")
    print(f"  Mean RPM error: {mean_rpm_error_on:.2f} RPM")
    print(f"  Max RPM error:  {max_rpm_error_on:.2f} RPM")

    # Comparison
    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")

    improvement_pct = (mean_rpm_error_off - mean_rpm_error_on) / mean_rpm_error_off * 100

    print(f"Mean RPM Error:")
    print(f"  OFF: {mean_rpm_error_off:.2f} RPM")
    print(f"  ON:  {mean_rpm_error_on:.2f} RPM")
    print(f"  Improvement: {improvement_pct:.1f}% reduction")

    print(f"\nMax RPM Error:")
    print(f"  OFF: {max_rpm_error_off:.2f} RPM")
    print(f"  ON:  {max_rpm_error_on:.2f} RPM")

    print(f"\n{'='*60}")
    if improvement_pct > 50:
        print("✅ SYNCHROPHASER HIGHLY EFFECTIVE!")
    elif improvement_pct > 20:
        print("✅ SYNCHROPHASER EFFECTIVE")
    elif improvement_pct > 0:
        print("⚠️  SYNCHROPHASER MARGINALLY EFFECTIVE")
    else:
        print("❌ SYNCHROPHASER NOT EFFECTIVE")
    print(f"{'='*60}")

if __name__ == '__main__':
    test_twin_propellers()
