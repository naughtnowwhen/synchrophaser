"""
Validation tools for atmospheric density field simulation.

Provides frequency analysis, spatial statistics, and physics verification
to ensure the density field behaves according to atmospheric turbulence theory.
"""

import numpy as np
from typing import Tuple, Dict
from scipy import signal, stats

from parameters import FREQUENCY_MIN, FREQUENCY_MAX


class DensityFieldValidator:
    """
    Validation and diagnostic tools for DensityField.

    Verifies that the generated field has correct:
    - Frequency content (via FFT)
    - Spatial wavelength characteristics
    - Statistical properties (distribution, moments)
    - Drift behavior (Taylor's frozen turbulence hypothesis)
    """

    @staticmethod
    def frequency_analysis(
        density_field,
        x: float,
        y: float,
        duration: float = 60.0,
        sample_rate: float = 30.0,
    ) -> Dict[str, np.ndarray]:
        """
        Analyze frequency content of density at a fixed spatial point.

        Samples density over time at position (x, y) and computes FFT.
        According to Taylor's frozen turbulence: f = V/λ

        For V=50 m/s and λ=150m, expect peak around f ≈ 0.33 Hz

        Args:
            density_field: DensityField instance to analyze
            x, y: Fixed spatial position (meters)
            duration: Time duration to sample (seconds)
            sample_rate: Samples per second (Hz)

        Returns:
            Dictionary with keys:
                'times': Time array
                'density': Sampled density values
                'frequencies': FFT frequency bins
                'power': Power spectral density
                'peak_frequency': Frequency with maximum power
                'expected_frequency': Theoretical peak from V/λ
        """
        # Generate time series at fixed point
        times = np.arange(0, duration, 1.0 / sample_rate)
        density_values = np.array(
            [density_field.get_density(x, y, t) for t in times]
        )

        # Remove mean (we care about variations, not absolute level)
        density_centered = density_values - np.mean(density_values)

        # Compute power spectral density using Welch's method
        # This averages multiple FFT windows for smoother spectrum
        frequencies, psd = signal.welch(
            density_centered,
            fs=sample_rate,
            nperseg=min(256, len(density_centered) // 4),
            scaling='density',
        )

        # Find peak frequency in range of interest
        mask = (frequencies >= FREQUENCY_MIN) & (frequencies <= FREQUENCY_MAX)
        if np.any(mask):
            peak_idx = np.argmax(psd[mask])
            peak_frequency = frequencies[mask][peak_idx]
        else:
            peak_frequency = 0.0

        # Calculate expected frequency from Taylor's hypothesis
        # f = V / λ
        expected_frequency = density_field.drift_velocity / density_field.wavelength

        return {
            'times': times,
            'density': density_values,
            'frequencies': frequencies,
            'power': psd,
            'peak_frequency': peak_frequency,
            'expected_frequency': expected_frequency,
        }

    @staticmethod
    def spatial_analysis(
        density_grid: np.ndarray,
        x_coords: np.ndarray,
        y_coords: np.ndarray,
    ) -> Dict[str, float]:
        """
        Analyze spatial characteristics of density field.

        Computes statistics and tries to estimate dominant wavelength
        from spatial autocorrelation.

        Args:
            density_grid: 2D array of densities
            x_coords: 1D array of x coordinates
            y_coords: 1D array of y coordinates

        Returns:
            Dictionary with spatial statistics
        """
        # Basic statistics
        stats_dict = {
            'mean': np.mean(density_grid),
            'std': np.std(density_grid),
            'min': np.min(density_grid),
            'max': np.max(density_grid),
            'range': np.ptp(density_grid),
        }

        # Check if distribution is approximately Gaussian
        # Atmospheric turbulence often has near-Gaussian density variations
        flat_data = density_grid.flatten()
        _, p_value = stats.normaltest(flat_data)
        stats_dict['gaussian_p_value'] = p_value
        stats_dict['is_gaussian_like'] = p_value > 0.05  # 5% significance

        # Estimate dominant wavelength from horizontal autocorrelation
        # Take middle row and compute autocorrelation
        middle_row_idx = len(y_coords) // 2
        middle_row = density_grid[middle_row_idx, :]

        # Normalize
        middle_row_centered = middle_row - np.mean(middle_row)

        # Compute autocorrelation
        autocorr = np.correlate(
            middle_row_centered, middle_row_centered, mode='full'
        )
        autocorr = autocorr[len(autocorr) // 2 :]  # Keep positive lags only
        autocorr /= autocorr[0]  # Normalize so autocorr[0] = 1

        # Find first zero crossing (rough wavelength estimate)
        zero_crossings = np.where(np.diff(np.sign(autocorr)))[0]
        if len(zero_crossings) > 0:
            first_zero_idx = zero_crossings[0]
            dx = x_coords[1] - x_coords[0] if len(x_coords) > 1 else 1.0
            estimated_wavelength = first_zero_idx * dx
            stats_dict['estimated_wavelength'] = estimated_wavelength
        else:
            stats_dict['estimated_wavelength'] = None

        return stats_dict

    @staticmethod
    def verify_drift(
        density_field,
        x: float,
        y: float,
        dt: float = 1.0,
    ) -> Dict[str, float]:
        """
        Verify that density field drifts correctly.

        According to Taylor's frozen turbulence hypothesis:
        ρ(x, t) ≈ ρ(x + V·Δt, t + Δt)

        The pattern should advect rigidly with the drift velocity.

        Args:
            density_field: DensityField instance
            x, y: Test position
            dt: Time step to test

        Returns:
            Dictionary with drift verification metrics
        """
        # Sample density at (x, t)
        rho_1 = density_field.get_density(x, y, time=0.0)

        # Sample at (x + V*dt, t + dt) - should be nearly the same
        x_shifted = x + density_field.drift_velocity * dt
        rho_2 = density_field.get_density(x_shifted, y, time=dt)

        # Calculate error
        absolute_error = abs(rho_2 - rho_1)
        relative_error = absolute_error / (density_field.rho_max - density_field.rho_min)

        return {
            'rho_at_t0': rho_1,
            'rho_at_t1_shifted': rho_2,
            'absolute_error': absolute_error,
            'relative_error': relative_error,
            'is_drifting_correctly': relative_error < 0.01,  # < 1% error
        }

    @staticmethod
    def export_snapshot(
        density_grid: np.ndarray,
        x_coords: np.ndarray,
        y_coords: np.ndarray,
        filename: str,
        file_format: str = 'npz',
    ):
        """
        Export density field snapshot for later analysis.

        Args:
            density_grid: 2D density array
            x_coords: 1D x coordinate array
            y_coords: 1D y coordinate array
            filename: Output filename (without extension)
            file_format: 'npz' (numpy) or 'csv'
        """
        if file_format == 'npz':
            np.savez(
                f"{filename}.npz",
                density=density_grid,
                x=x_coords,
                y=y_coords,
            )
        elif file_format == 'csv':
            # CSV format: flatten grid with coordinates
            X, Y = np.meshgrid(x_coords, y_coords)
            data = np.column_stack([
                X.flatten(),
                Y.flatten(),
                density_grid.flatten(),
            ])
            np.savetxt(
                f"{filename}.csv",
                data,
                delimiter=',',
                header='x_meters,y_meters,density_kg_m3',
                comments='',
            )
        else:
            raise ValueError(f"Unknown format: {file_format}")

    @staticmethod
    def print_validation_report(
        density_field,
        density_grid: np.ndarray,
        x_coords: np.ndarray,
        y_coords: np.ndarray,
    ):
        """
        Print comprehensive validation report to console.

        Args:
            density_field: DensityField instance
            density_grid: Current density grid
            x_coords: X coordinate array
            y_coords: Y coordinate array
        """
        print("=" * 60)
        print("DENSITY FIELD VALIDATION REPORT")
        print("=" * 60)

        print("\n--- PARAMETERS ---")
        print(f"Wavelength: {density_field.wavelength:.1f} m")
        print(f"Density range: [{density_field.rho_min:.3f}, {density_field.rho_max:.3f}] kg/m³")
        print(f"Drift velocity: {density_field.drift_velocity:.1f} m/s")
        print(f"Num octaves: {density_field.num_octaves}")
        print(f"Expected frequency (V/λ): {density_field.drift_velocity/density_field.wavelength:.3f} Hz")

        print("\n--- SPATIAL STATISTICS ---")
        spatial_stats = DensityFieldValidator.spatial_analysis(
            density_grid, x_coords, y_coords
        )
        print(f"Mean: {spatial_stats['mean']:.4f} kg/m³")
        print(f"Std Dev: {spatial_stats['std']:.4f} kg/m³")
        print(f"Range: [{spatial_stats['min']:.4f}, {spatial_stats['max']:.4f}] kg/m³")
        print(f"Gaussian-like: {spatial_stats['is_gaussian_like']} (p={spatial_stats['gaussian_p_value']:.3f})")
        if spatial_stats['estimated_wavelength']:
            print(f"Estimated wavelength: {spatial_stats['estimated_wavelength']:.1f} m")

        print("\n--- DRIFT VERIFICATION ---")
        drift_check = DensityFieldValidator.verify_drift(
            density_field, x=500.0, y=0.0, dt=1.0
        )
        print(f"Relative error: {drift_check['relative_error']:.4f}")
        print(f"Drift correct: {drift_check['is_drifting_correctly']}")

        print("\n" + "=" * 60)
