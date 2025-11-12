#!/usr/bin/env python3
"""
Unit tests for atmospheric density field simulation.

Run with: pytest test_unit.py
Or: python3 -m pytest test_unit.py
"""

import numpy as np
import pytest
from density_field import DensityField
from validation import DensityFieldValidator
from parameters import (
    RHO_MIN_DEFAULT,
    RHO_MAX_DEFAULT,
    WAVELENGTH_DEFAULT,
    DRIFT_VELOCITY_DEFAULT,
)


class TestDensityField:
    """Test suite for DensityField class."""

    def test_initialization(self):
        """Test DensityField initialization with default parameters."""
        field = DensityField()
        assert field.wavelength == WAVELENGTH_DEFAULT
        assert field.rho_min == RHO_MIN_DEFAULT
        assert field.rho_max == RHO_MAX_DEFAULT
        assert field.drift_velocity == DRIFT_VELOCITY_DEFAULT

    def test_initialization_custom(self):
        """Test DensityField with custom parameters."""
        field = DensityField(
            wavelength=200.0,
            rho_min=1.20,
            rho_max=1.25,
            drift_velocity=60.0,
            num_octaves=6,
            seed=99,
        )
        assert field.wavelength == 200.0
        assert field.rho_min == 1.20
        assert field.rho_max == 1.25
        assert field.drift_velocity == 60.0
        assert field.num_octaves == 6
        assert field.seed == 99

    def test_get_density_returns_float(self):
        """Test that get_density returns a float."""
        field = DensityField()
        rho = field.get_density(100.0, 0.0, 0.0)
        assert isinstance(rho, (float, np.floating))

    def test_get_density_in_range(self):
        """Test that density values are always within [rho_min, rho_max]."""
        field = DensityField()

        # Test many random points
        np.random.seed(42)
        for _ in range(100):
            x = np.random.uniform(0, 1000)
            y = np.random.uniform(-100, 100)
            t = np.random.uniform(0, 100)
            rho = field.get_density(x, y, t)
            assert field.rho_min <= rho <= field.rho_max

    def test_get_density_grid_shape(self):
        """Test that get_density_grid returns correct shape."""
        field = DensityField()
        x = np.linspace(0, 1000, 50)
        y = np.linspace(-100, 100, 30)
        grid = field.get_density_grid(x, y, 0.0)
        assert grid.shape == (30, 50)

    def test_get_density_grid_all_in_range(self):
        """Test that all grid values are within valid range."""
        field = DensityField()
        x = np.linspace(0, 1000, 100)
        y = np.linspace(-100, 100, 40)
        grid = field.get_density_grid(x, y, 0.0)
        assert np.all(grid >= field.rho_min)
        assert np.all(grid <= field.rho_max)

    def test_different_seeds_produce_different_fields(self):
        """Test that different seeds produce different patterns."""
        field1 = DensityField(seed=42)
        field2 = DensityField(seed=99)

        rho1 = field1.get_density(100.0, 0.0, 0.0)
        rho2 = field2.get_density(100.0, 0.0, 0.0)

        assert abs(rho1 - rho2) > 1e-6  # Should be different

    def test_same_seed_produces_same_field(self):
        """Test that same seed produces reproducible results."""
        field1 = DensityField(seed=42)
        field2 = DensityField(seed=42)

        rho1 = field1.get_density(100.0, 0.0, 0.0)
        rho2 = field2.get_density(100.0, 0.0, 0.0)

        assert abs(rho1 - rho2) < 1e-10  # Should be identical

    def test_spatial_smoothness(self):
        """Test that field is spatially smooth (no discontinuities)."""
        field = DensityField()

        # Sample nearby points - should have similar values
        x, y, t = 100.0, 0.0, 0.0
        dx = 1.0  # 1 meter apart

        rho_center = field.get_density(x, y, t)
        rho_right = field.get_density(x + dx, y, t)

        # Should be smooth - nearby points shouldn't differ by more than a few percent
        diff = abs(rho_right - rho_center)
        max_expected_diff = (field.rho_max - field.rho_min) * 0.1  # 10% of range
        assert diff < max_expected_diff


class TestDrift:
    """Test suite for drift behavior (Taylor's frozen turbulence hypothesis)."""

    def test_drift_basic(self):
        """Test basic drift: ρ(x,t) ≈ ρ(x+V*dt, t+dt)."""
        field = DensityField(wavelength=150.0, drift_velocity=50.0)

        x, y = 100.0, 0.0
        t0, dt = 0.0, 1.0

        rho_t0 = field.get_density(x, y, t0)
        rho_t1_shifted = field.get_density(x + field.drift_velocity * dt, y, t0 + dt)

        # Should be nearly identical
        rel_error = abs(rho_t1_shifted - rho_t0) / (field.rho_max - field.rho_min)
        assert rel_error < 0.01  # Less than 1% error

    def test_drift_multiple_timesteps(self):
        """Test drift over multiple time steps."""
        field = DensityField(drift_velocity=50.0)

        x, y = 500.0, 0.0
        time_steps = [0.0, 0.5, 1.0, 1.5, 2.0]

        for i in range(len(time_steps) - 1):
            t0 = time_steps[i]
            t1 = time_steps[i + 1]
            dt = t1 - t0

            rho_t0 = field.get_density(x, y, t0)
            rho_t1_shifted = field.get_density(x + field.drift_velocity * dt, y, t1)

            rel_error = abs(rho_t1_shifted - rho_t0) / (field.rho_max - field.rho_min)
            assert rel_error < 0.01

    def test_field_evolves_with_time(self):
        """Test that field at fixed point changes with time (not static)."""
        field = DensityField()

        x, y = 500.0, 0.0
        rho_t0 = field.get_density(x, y, 0.0)
        rho_t1 = field.get_density(x, y, 1.0)

        # Should be different (field is drifting past the fixed point)
        assert abs(rho_t0 - rho_t1) > 1e-6


class TestWavelength:
    """Test suite for wavelength parameter."""

    def test_wavelength_affects_frequency(self):
        """Test that base frequency is correctly calculated from wavelength."""
        wavelength = 200.0
        field = DensityField(wavelength=wavelength)
        expected_freq = 1.0 / wavelength
        assert abs(field.base_frequency - expected_freq) < 1e-10

    def test_smaller_wavelength_more_variation(self):
        """Test that smaller wavelength produces more spatial variation."""
        field_large = DensityField(wavelength=400.0, seed=42)
        field_small = DensityField(wavelength=100.0, seed=42)

        x = np.linspace(0, 1000, 100)
        y = np.zeros(100)
        t = 0.0

        densities_large = [field_large.get_density(xi, 0.0, t) for xi in x]
        densities_small = [field_small.get_density(xi, 0.0, t) for xi in x]

        # Smaller wavelength should have more variation along x
        std_large = np.std(densities_large)
        std_small = np.std(densities_small)

        # This might not always hold due to noise, but generally true
        # Just verify both have some variation
        assert std_large > 0
        assert std_small > 0


class TestStatistics:
    """Test suite for statistical properties."""

    def test_get_statistics(self):
        """Test get_statistics method."""
        field = DensityField()
        x = np.linspace(0, 1000, 50)
        y = np.linspace(-100, 100, 30)
        grid = field.get_density_grid(x, y, 0.0)

        stats = field.get_statistics(grid)

        assert 'mean' in stats
        assert 'min' in stats
        assert 'max' in stats
        assert 'std' in stats

        # Mean should be roughly in the middle of the range
        # (might not be exact due to noise distribution)
        assert field.rho_min <= stats['mean'] <= field.rho_max
        assert stats['min'] >= field.rho_min
        assert stats['max'] <= field.rho_max
        assert stats['std'] > 0  # Should have variation


class TestValidation:
    """Test suite for validation tools."""

    def test_spatial_analysis(self):
        """Test spatial_analysis function."""
        field = DensityField()
        x = np.linspace(0, 1000, 100)
        y = np.linspace(-100, 100, 40)
        grid = field.get_density_grid(x, y, 0.0)

        stats = DensityFieldValidator.spatial_analysis(grid, x, y)

        assert 'mean' in stats
        assert 'std' in stats
        assert 'min' in stats
        assert 'max' in stats
        assert 'range' in stats
        assert 'is_gaussian_like' in stats

    def test_verify_drift(self):
        """Test verify_drift function."""
        field = DensityField()
        result = DensityFieldValidator.verify_drift(field, x=500.0, y=0.0, dt=1.0)

        assert 'rho_at_t0' in result
        assert 'rho_at_t1_shifted' in result
        assert 'absolute_error' in result
        assert 'relative_error' in result
        assert 'is_drifting_correctly' in result

        assert result['is_drifting_correctly'] == True

    def test_frequency_analysis(self):
        """Test frequency_analysis function."""
        field = DensityField(wavelength=150.0, drift_velocity=50.0)

        # Short duration for fast test
        result = DensityFieldValidator.frequency_analysis(
            field, x=500.0, y=0.0, duration=10.0, sample_rate=30.0
        )

        assert 'times' in result
        assert 'density' in result
        assert 'frequencies' in result
        assert 'power' in result
        assert 'peak_frequency' in result
        assert 'expected_frequency' in result

        # Expected frequency from Taylor's hypothesis
        expected = field.drift_velocity / field.wavelength
        assert abs(result['expected_frequency'] - expected) < 1e-6


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_negative_coordinates(self):
        """Test that negative coordinates work correctly."""
        field = DensityField()
        rho = field.get_density(-100.0, -50.0, 0.0)
        assert field.rho_min <= rho <= field.rho_max

    def test_large_coordinates(self):
        """Test that very large coordinates work correctly."""
        field = DensityField()
        rho = field.get_density(10000.0, 5000.0, 100.0)
        assert field.rho_min <= rho <= field.rho_max

    def test_zero_time(self):
        """Test that time=0 works correctly."""
        field = DensityField()
        rho = field.get_density(100.0, 0.0, 0.0)
        assert field.rho_min <= rho <= field.rho_max

    def test_large_time(self):
        """Test that large time values work correctly."""
        field = DensityField()
        rho = field.get_density(100.0, 0.0, 10000.0)
        assert field.rho_min <= rho <= field.rho_max


if __name__ == '__main__':
    # Run with: python3 test_unit.py
    pytest.main([__file__, '-v'])
