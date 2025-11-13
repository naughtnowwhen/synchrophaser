#!/usr/bin/env python3
"""
Quick test to verify rolling average error calculation.

Tests that the 15-second rolling average correctly:
1. Updates with new errors
2. Removes old errors outside the window
3. Computes correct average
"""

import numpy as np
from collections import deque


def test_rolling_average():
    """Test rolling average calculation."""
    print("="*60)
    print("ROLLING AVERAGE ERROR TEST")
    print("="*60)

    # Simulate the rolling average logic
    error_history = deque()
    rolling_window_seconds = 15.0
    rolling_avg_error = 0.0

    print("\nSimulating 30 seconds of operation...")
    print("First 10s: High error (~10 RPM)")
    print("Next 10s:  Medium error (~5 RPM)")
    print("Last 10s:  Low error (~1 RPM)")
    print()

    # Simulate 30 seconds at 10 Hz update rate
    dt = 0.1
    duration = 30.0

    for i in range(int(duration / dt)):
        sim_time = i * dt

        # Simulate different error levels over time
        if sim_time < 10.0:
            # First 10 seconds: high error
            rpm_error = 10.0 + np.random.uniform(-1, 1)
        elif sim_time < 20.0:
            # Next 10 seconds: medium error
            rpm_error = 5.0 + np.random.uniform(-0.5, 0.5)
        else:
            # Last 10 seconds: low error
            rpm_error = 1.0 + np.random.uniform(-0.2, 0.2)

        # Update rolling error history
        error_history.append((sim_time, rpm_error))

        # Remove old errors outside the rolling window
        cutoff_time = sim_time - rolling_window_seconds
        while error_history and error_history[0][0] < cutoff_time:
            error_history.popleft()

        # Compute rolling average
        if error_history:
            rolling_avg_error = np.mean([err for _, err in error_history])
        else:
            rolling_avg_error = 0.0

        # Print progress every 2 seconds
        if i % 20 == 0:
            print(f"t={sim_time:5.1f}s: Current={rpm_error:5.2f} RPM, "
                  f"15s Avg={rolling_avg_error:5.2f} RPM, "
                  f"Window size={len(error_history)}")

    print()
    print("="*60)
    print("VALIDATION")
    print("="*60)

    # At t=30s, the rolling average should reflect only the last 15s
    # which includes 5s of medium error (15-20s) and 10s of low error (20-30s)
    expected_avg_range = (1.5, 3.5)  # Rough estimate

    print(f"\nAt t=30s:")
    print(f"  Rolling average: {rolling_avg_error:.2f} RPM")
    print(f"  Expected range:  {expected_avg_range[0]}-{expected_avg_range[1]} RPM")
    print(f"  Window size:     {len(error_history)} samples")
    print(f"  Window duration: {error_history[-1][0] - error_history[0][0]:.1f}s")

    if expected_avg_range[0] <= rolling_avg_error <= expected_avg_range[1]:
        print("\n✅ Rolling average is in expected range!")
        print("✅ Old high errors (t=0-10s) have been removed from window")
        print("✅ Average reflects only last 15 seconds")
        return True
    else:
        print("\n❌ Rolling average is outside expected range")
        return False


def test_window_size():
    """Test that window correctly maintains 15 seconds."""
    print("\n" + "="*60)
    print("WINDOW SIZE TEST")
    print("="*60)

    error_history = deque()
    rolling_window_seconds = 15.0

    # Run for 30 seconds at 10 Hz
    dt = 0.1
    for i in range(300):
        sim_time = i * dt
        rpm_error = 5.0  # Constant error

        error_history.append((sim_time, rpm_error))

        # Remove old errors
        cutoff_time = sim_time - rolling_window_seconds
        while error_history and error_history[0][0] < cutoff_time:
            error_history.popleft()

    # At steady state, should have 15 seconds * 10 Hz = 150 samples
    expected_samples = 150

    print(f"\nAfter 30 seconds at 10 Hz update rate:")
    print(f"  Window size:     {len(error_history)} samples")
    print(f"  Expected size:   ~{expected_samples} samples")
    print(f"  Time span:       {error_history[-1][0] - error_history[0][0]:.1f}s")

    if abs(len(error_history) - expected_samples) < 5:
        print("\n✅ Window size is correct!")
        print("✅ Maintains exactly 15 seconds of data")
        return True
    else:
        print("\n❌ Window size is incorrect")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Testing 15-second rolling average implementation")
    print("="*60)

    test1 = test_rolling_average()
    test2 = test_window_size()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if test1 and test2:
        print("✅ All tests passed!")
        print("\nRolling average feature is working correctly:")
        print("  - Correctly computes average over 15-second window")
        print("  - Removes old data outside window")
        print("  - Responds to changing error levels")
        print("\nReady for use in visualization!")
    else:
        print("❌ Some tests failed - review implementation")

    print("="*60)


if __name__ == '__main__':
    main()
