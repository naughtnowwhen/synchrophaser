#!/usr/bin/env python3
"""
Quick tests to verify basic functionality of the density field simulation.
Run this before launching the full visualization.
"""

import numpy as np
import sys

def test_imports():
    """Test that all modules import correctly."""
    print("Testing imports...")
    try:
        from density_field import DensityField
        from validation import DensityFieldValidator
        import parameters
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_density_field():
    """Test basic DensityField functionality."""
    print("\nTesting DensityField class...")
    from density_field import DensityField

    # Create field
    field = DensityField(wavelength=150.0, rho_min=1.15, rho_max=1.30)
    print(f"  ✓ Created DensityField")

    # Test single point sampling
    rho = field.get_density(100.0, 0.0, 0.0)
    print(f"  ✓ get_density(100, 0, 0) = {rho:.4f} kg/m³")

    # Verify density is in range
    assert field.rho_min <= rho <= field.rho_max, "Density out of range!"
    print(f"  ✓ Density in valid range [{field.rho_min}, {field.rho_max}]")

    # Test grid sampling
    x = np.linspace(0, 1000, 50)
    y = np.linspace(-100, 100, 20)
    grid = field.get_density_grid(x, y, 0.0)
    print(f"  ✓ get_density_grid() produced shape {grid.shape}")

    # Verify all grid values in range
    assert np.all(grid >= field.rho_min) and np.all(grid <= field.rho_max), "Grid values out of range!"
    print(f"  ✓ All grid values in valid range")

    # Test statistics
    stats = field.get_statistics(grid)
    print(f"  ✓ Statistics: mean={stats['mean']:.4f}, std={stats['std']:.4f}")

    return True

def test_drift():
    """Test that drift works correctly."""
    print("\nTesting drift behavior...")
    from density_field import DensityField

    field = DensityField(wavelength=150.0, drift_velocity=50.0)

    # Sample at (x, t=0)
    x, y, t = 100.0, 0.0, 0.0
    rho_1 = field.get_density(x, y, t)

    # Sample at (x + V*dt, t=dt) - should be nearly the same
    dt = 1.0
    x_shifted = x + field.drift_velocity * dt
    rho_2 = field.get_density(x_shifted, y, t + dt)

    error = abs(rho_2 - rho_1)
    rel_error = error / (field.rho_max - field.rho_min)

    print(f"  ✓ ρ(x={x}, t={t}) = {rho_1:.4f}")
    print(f"  ✓ ρ(x={x_shifted}, t={t+dt}) = {rho_2:.4f}")
    print(f"  ✓ Relative error: {rel_error:.4f} (should be < 0.01)")

    assert rel_error < 0.01, "Drift error too large!"
    print(f"  ✓ Drift behavior correct (Taylor's hypothesis verified)")

    return True

def test_time_evolution():
    """Test that field evolves over time."""
    print("\nTesting time evolution...")
    from density_field import DensityField

    field = DensityField(wavelength=150.0, drift_velocity=50.0)

    # Sample same location at different times
    x, y = 500.0, 0.0
    rho_t0 = field.get_density(x, y, 0.0)
    rho_t1 = field.get_density(x, y, 1.0)
    rho_t2 = field.get_density(x, y, 2.0)

    print(f"  ✓ ρ(x={x}, t=0) = {rho_t0:.4f}")
    print(f"  ✓ ρ(x={x}, t=1) = {rho_t1:.4f}")
    print(f"  ✓ ρ(x={x}, t=2) = {rho_t2:.4f}")

    # Values should be different (field is drifting)
    assert abs(rho_t0 - rho_t1) > 1e-6, "Field not evolving!"
    print(f"  ✓ Field evolves with time (not static)")

    return True

def test_validation_tools():
    """Test validation module."""
    print("\nTesting validation tools...")
    from density_field import DensityField
    from validation import DensityFieldValidator

    field = DensityField()

    # Test spatial analysis
    x = np.linspace(0, 1000, 50)
    y = np.linspace(-100, 100, 20)
    grid = field.get_density_grid(x, y, 0.0)

    stats = DensityFieldValidator.spatial_analysis(grid, x, y)
    print(f"  ✓ Spatial analysis: mean={stats['mean']:.4f}, std={stats['std']:.4f}")

    # Test drift verification
    drift_check = DensityFieldValidator.verify_drift(field, 500.0, 0.0, dt=1.0)
    print(f"  ✓ Drift verification: error={drift_check['relative_error']:.4f}")

    assert drift_check['is_drifting_correctly'], "Drift verification failed!"
    print(f"  ✓ Drift verification passed")

    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("RUNNING BASIC FUNCTIONALITY TESTS")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("DensityField", test_density_field),
        ("Drift", test_drift),
        ("Time Evolution", test_time_evolution),
        ("Validation Tools", test_validation_tools),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ {name} test failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name} test failed with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✓ All tests passed! Ready to run visualization.")
        print("  Run: python main.py")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix before running visualization.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
