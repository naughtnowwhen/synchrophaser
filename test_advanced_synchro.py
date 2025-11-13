"""
Test advanced synchrophaser with Kalman filtering.

Compares three modes:
1. OFF - No synchronization
2. BASELINE - Proven PID with filtering
3. ADVANCED - Kalman filter + PID

Validates that advanced mode improves upon baseline.
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
)


def run_test_phase(
    name: str,
    duration: float,
    synchro,
    use_synchro: bool,
) -> dict:
    """
    Run one test phase and collect metrics.

    Args:
        name: Test phase name (for display)
        duration: Test duration in seconds
        synchro: Synchrophaser instance (or None)
        use_synchro: Whether to enable synchrophaser

    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*60}")
    print(f"TEST: {name} ({duration:.0f} seconds)")
    print(f"{'='*60}")

    # Create fresh density field and propellers
    field = DensityField()
    prop_main = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_LEFT_Y)
    prop_follower = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_RIGHT_Y)

    # Enable/disable synchrophaser
    if synchro and use_synchro:
        synchro.enable()
    elif synchro:
        synchro.disable()

    # Storage for metrics
    rpm_errors = []
    phase_errors = []
    rpm_corrections = []

    # Simulation parameters
    dt = 0.01  # 100 Hz update rate
    follower_base_rpm = PROPELLER_RPM_NOMINAL

    # Run simulation
    for i in range(int(duration / dt)):
        t = i * dt

        # Update propellers (independent physics!)
        prop_main.update(dt, t, field)
        prop_follower.update(dt, t, field)

        # Update synchrophaser if enabled
        rpm_correction = 0.0
        if synchro and use_synchro:
            # Check if this is a PFD synchrophaser (needs omega values)
            if isinstance(synchro, PFDSynchrophaser):
                rpm_correction = synchro.update(
                    prop_main.blade_angle,
                    prop_follower.blade_angle,
                    prop_main.omega,
                    prop_follower.omega,
                    dt
                )
            else:
                # Regular synchrophaser (only needs blade angles)
                rpm_correction = synchro.update(
                    prop_main.blade_angle,
                    prop_follower.blade_angle,
                    dt
                )
            # Apply correction to follower's governor setpoint
            new_target = follower_base_rpm + rpm_correction
            new_target = np.clip(new_target, 2350, 2450)
            prop_follower.set_rpm_target(new_target)
        else:
            # When disabled, maintain base RPM
            prop_follower.set_rpm_target(follower_base_rpm)
            if synchro:
                # Still update synchro for phase tracking (but disabled)
                if isinstance(synchro, PFDSynchrophaser):
                    synchro.update(prop_main.blade_angle, prop_follower.blade_angle,
                                 prop_main.omega, prop_follower.omega, dt)
                else:
                    synchro.update(prop_main.blade_angle, prop_follower.blade_angle, dt)

        # Collect metrics
        rpm_error = abs(prop_main.rpm - prop_follower.rpm)
        rpm_errors.append(rpm_error)
        rpm_corrections.append(rpm_correction)

        if synchro:
            phase_errors.append(abs(synchro.phase_error))
        else:
            # Compute phase error manually
            phase_err = prop_main.blade_angle - prop_follower.blade_angle
            phase_err = np.arctan2(np.sin(phase_err), np.cos(phase_err))
            phase_errors.append(abs(phase_err))

        # Print progress
        if i % (5.0 / dt) == 0:  # Every 5 seconds
            print(f"t={t:5.1f}s: Main={prop_main.rpm:7.1f}, "
                  f"Follower={prop_follower.rpm:7.1f}, "
                  f"Diff={rpm_error:4.1f} RPM, "
                  f"Corr={rpm_correction:+5.1f}")

    # Compute statistics
    results = {
        'mean_rpm_error': np.mean(rpm_errors),
        'max_rpm_error': np.max(rpm_errors),
        'std_rpm_error': np.std(rpm_errors),
        'mean_phase_error_deg': np.degrees(np.mean(phase_errors)),
        'max_phase_error_deg': np.degrees(np.max(phase_errors)),
        'mean_abs_correction': np.mean(np.abs(rpm_corrections)),
        'max_correction': np.max(np.abs(rpm_corrections)),
    }

    # Print results
    print(f"\nResults ({name}):")
    print(f"  Mean RPM error: {results['mean_rpm_error']:.2f} RPM")
    print(f"  Max RPM error:  {results['max_rpm_error']:.2f} RPM")
    print(f"  Mean phase error: {results['mean_phase_error_deg']:.2f}°")
    if use_synchro:
        print(f"  Mean correction: {results['mean_abs_correction']:.2f} RPM")
        print(f"  Max correction:  {results['max_correction']:.2f} RPM")

    return results


def main():
    """Run comparison test: OFF vs BASELINE vs ADVANCED."""
    print("="*60)
    print("ADVANCED SYNCHROPHASER COMPARISON TEST")
    print("="*60)
    print(f"\nPropeller positions:")
    print(f"  Main:     ({PROPELLER_X_DEFAULT:.0f}m, {PROPELLER_LEFT_Y:.0f}m)")
    print(f"  Follower: ({PROPELLER_X_DEFAULT:.0f}m, {PROPELLER_RIGHT_Y:.0f}m)")
    print(f"  Separation: {abs(PROPELLER_LEFT_Y - PROPELLER_RIGHT_Y):.0f}m")

    # Test duration (shorter for quick testing, increase for validation)
    duration = 30.0  # seconds

    # Phase 1: OFF (no synchrophaser)
    results_off = run_test_phase(
        name="Synchrophaser OFF",
        duration=duration,
        synchro=None,
        use_synchro=False,
    )

    # Phase 2: BASELINE (proven PID)
    synchro_baseline = Synchrophaser()
    results_baseline = run_test_phase(
        name="Synchrophaser BASELINE",
        duration=duration,
        synchro=synchro_baseline,
        use_synchro=True,
    )

    # Phase 3: ADVANCED (Phase-Frequency Detector)
    synchro_advanced = PFDSynchrophaser()
    results_advanced = run_test_phase(
        name="Synchrophaser ADVANCED (PFD)",
        duration=duration,
        synchro=synchro_advanced,
        use_synchro=True,
    )

    # Comparison
    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")

    print("\n📊 Mean RPM Error:")
    print(f"  OFF:      {results_off['mean_rpm_error']:.2f} RPM")
    print(f"  BASELINE: {results_baseline['mean_rpm_error']:.2f} RPM")
    print(f"  ADVANCED: {results_advanced['mean_rpm_error']:.2f} RPM")

    # Calculate improvements
    baseline_improvement = (
        (results_off['mean_rpm_error'] - results_baseline['mean_rpm_error']) /
        results_off['mean_rpm_error'] * 100
    )
    advanced_improvement = (
        (results_off['mean_rpm_error'] - results_advanced['mean_rpm_error']) /
        results_off['mean_rpm_error'] * 100
    )
    advanced_vs_baseline = (
        (results_baseline['mean_rpm_error'] - results_advanced['mean_rpm_error']) /
        results_baseline['mean_rpm_error'] * 100
    )

    print(f"\n📈 Improvements:")
    print(f"  Baseline vs OFF:     {baseline_improvement:+5.1f}% reduction")
    print(f"  Advanced vs OFF:     {advanced_improvement:+5.1f}% reduction")
    print(f"  Advanced vs Baseline: {advanced_vs_baseline:+5.1f}% reduction")

    print(f"\n📊 Max RPM Error:")
    print(f"  OFF:      {results_off['max_rpm_error']:.2f} RPM")
    print(f"  BASELINE: {results_baseline['max_rpm_error']:.2f} RPM")
    print(f"  ADVANCED: {results_advanced['max_rpm_error']:.2f} RPM")

    print(f"\n📐 Mean Phase Error:")
    print(f"  OFF:      {results_off['mean_phase_error_deg']:.2f}°")
    print(f"  BASELINE: {results_baseline['mean_phase_error_deg']:.2f}°")
    print(f"  ADVANCED: {results_advanced['mean_phase_error_deg']:.2f}°")

    # Validation
    print(f"\n{'='*60}")
    print("VALIDATION")
    print(f"{'='*60}")

    checks_passed = 0
    checks_total = 0

    # Check 1: Baseline improves over OFF
    checks_total += 1
    if baseline_improvement > 50:
        print("✅ Baseline shows good improvement (>50%)")
        checks_passed += 1
    else:
        print(f"⚠️  Baseline improvement marginal ({baseline_improvement:.1f}%)")

    # Check 2: Advanced improves over OFF
    checks_total += 1
    if advanced_improvement > 60:
        print("✅ Advanced shows good improvement (>60%)")
        checks_passed += 1
    else:
        print(f"⚠️  Advanced improvement marginal ({advanced_improvement:.1f}%)")

    # Check 3: Advanced improves over Baseline
    checks_total += 1
    if advanced_vs_baseline > 0:
        print(f"✅ Advanced better than Baseline (+{advanced_vs_baseline:.1f}%)")
        checks_passed += 1
    else:
        print(f"❌ Advanced WORSE than Baseline ({advanced_vs_baseline:.1f}%)")

    # Check 4: Advanced is stable (not making things worse)
    checks_total += 1
    if results_advanced['mean_rpm_error'] < results_off['mean_rpm_error']:
        print("✅ Advanced is stable (better than OFF)")
        checks_passed += 1
    else:
        print("❌ Advanced is UNSTABLE (worse than OFF)")

    print(f"\n{'='*60}")
    if checks_passed == checks_total:
        print(f"✅ ALL CHECKS PASSED ({checks_passed}/{checks_total})")
        print("Advanced synchrophaser validated!")
    else:
        print(f"⚠️  SOME CHECKS FAILED ({checks_passed}/{checks_total})")
        print("Review results before deploying advanced mode")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
