#!/usr/bin/env python3
"""
Quick test of propeller physics and dynamics.
"""

from density_field import DensityField
from propeller import Propeller
import numpy as np

def test_propeller_basic():
    """Test basic propeller functionality."""
    print("=" * 60)
    print("PROPELLER DYNAMICS TEST")
    print("=" * 60)

    # Create components
    field = DensityField(wavelength=150.0, drift_velocity=50.0)
    prop = Propeller()

    print(f"\n--- Initial State ---")
    print(f"Position: ({prop.x}, {prop.y}) m")
    print(f"Target RPM: {prop.rpm_nominal}")
    print(f"Inertia: {prop.inertia} kg·m²")
    print(f"K_aero: {prop.k_aero}")
    print(f"Governor K_P: {prop.governor_kp}")

    # Simulate for several seconds
    print(f"\n--- Simulation (10 seconds) ---")
    dt = 0.01  # 10ms time steps
    history_t = []
    history_rpm = []
    history_rho = []

    for i in range(1000):  # 10 seconds
        t = i * dt
        prop.update(dt, t, field)

        history_t.append(t)
        history_rpm.append(prop.rpm)
        history_rho.append(prop.rho_local)

        if i % 200 == 0:  # Print every 2 seconds
            print(f"t={t:4.1f}s: RPM={prop.rpm:7.1f}, "
                  f"ρ={prop.rho_local:.4f} kg/m³, "
                  f"Q_aero={prop.q_aero:6.1f} Nm, "
                  f"Q_eng={prop.q_engine:6.1f} Nm")

    # Statistics
    rpm_array = np.array(history_rpm)
    rho_array = np.array(history_rho)

    print(f"\n--- Statistics ---")
    print(f"RPM mean: {rpm_array.mean():.2f}")
    print(f"RPM std:  {rpm_array.std():.2f}")
    print(f"RPM min:  {rpm_array.min():.2f}")
    print(f"RPM max:  {rpm_array.max():.2f}")
    print(f"RPM range: {rpm_array.max() - rpm_array.min():.2f}")
    print(f"\nDensity mean: {rho_array.mean():.4f} kg/m³")
    print(f"Density std:  {rho_array.std():.4f} kg/m³")
    print(f"Density range: [{rho_array.min():.4f}, {rho_array.max():.4f}]")

    # Check governor performance
    rpm_error = abs(rpm_array.mean() - prop.rpm_nominal)
    rpm_variation = rpm_array.std()

    print(f"\n--- Governor Performance ---")
    print(f"Mean error: {rpm_error:.2f} RPM")
    print(f"Variation (std): {rpm_variation:.2f} RPM")
    print(f"Governor effective: {rpm_error < 10 and rpm_variation < 20}")

    print("\n" + "=" * 60)
    print("✓ TEST PASSED" if rpm_error < 10 else "✗ TEST FAILED")
    print("=" * 60)

if __name__ == '__main__':
    test_propeller_basic()
