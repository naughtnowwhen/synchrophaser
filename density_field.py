"""
Atmospheric density field using OpenSimplex noise with fractal Brownian motion.

Generates smooth, time-varying density variations representing atmospheric turbulence.
The field drifts horizontally to simulate apparent motion through turbulent air.
"""

import numpy as np
from opensimplex import OpenSimplex

from parameters import (
    WAVELENGTH_DEFAULT,
    RHO_MIN_DEFAULT,
    RHO_MAX_DEFAULT,
    DRIFT_VELOCITY_DEFAULT,
    NUM_OCTAVES_DEFAULT,
    PERSISTENCE,
    LACUNARITY,
    DEFAULT_SEED,
)


class DensityField:
    """
    Atmospheric density field using Perlin/OpenSimplex noise.

    Generates smooth, time-varying density variations based on fractal
    Brownian motion (fBm). The field drifts horizontally at a specified
    velocity to simulate motion through turbulent air.

    Physics basis:
    - Density range represents realistic atmospheric variations
    - Wavelength corresponds to turbulence integral length scales (50-500m)
    - Drift velocity represents aircraft cruise speed through air mass
    - Multiple octaves create realistic multi-scale turbulence structure

    Key interface for future propeller integration:
        rho = field.get_density(x, y, time)
    """

    def __init__(
        self,
        wavelength: float = WAVELENGTH_DEFAULT,
        rho_min: float = RHO_MIN_DEFAULT,
        rho_max: float = RHO_MAX_DEFAULT,
        drift_velocity: float = DRIFT_VELOCITY_DEFAULT,
        num_octaves: int = NUM_OCTAVES_DEFAULT,
        seed: int = DEFAULT_SEED,
    ):
        """
        Initialize atmospheric density field.

        Args:
            wavelength: Dominant turbulence scale in meters (50-500m typical)
            rho_min: Minimum density in kg/m³ (default 1.15)
            rho_max: Maximum density in kg/m³ (default 1.30)
            drift_velocity: Apparent wind speed in m/s (default 50 m/s ≈ 100 knots)
            num_octaves: Number of noise layers for fBm (1-6, default 4)
            seed: Random seed for reproducible noise generation
        """
        self.wavelength = wavelength
        self.rho_min = rho_min
        self.rho_max = rho_max
        self.drift_velocity = drift_velocity
        self.num_octaves = num_octaves
        self.seed = seed

        # Initialize OpenSimplex noise generator
        # OpenSimplex is patent-free (as of Jan 2022) and produces smooth gradients
        self.noise = OpenSimplex(seed=seed)

        # Calculate base frequency from wavelength
        # Smaller wavelength = higher frequency = more variation per meter
        self.base_frequency = 1.0 / wavelength

        # Pre-calculate normalization factor for fBm
        # This ensures the summed octaves map to approximately [0, 1]
        self.amplitude_sum = sum(PERSISTENCE ** i for i in range(num_octaves))

    def _fbm_noise_2d(self, x: float, y: float) -> float:
        """
        Generate 2D fractal Brownian motion noise at position (x, y).

        Combines multiple octaves of noise with decreasing amplitude and
        increasing frequency to create natural-looking turbulence.

        Args:
            x, y: Spatial coordinates in meters

        Returns:
            Noise value approximately in range [0, 1]
        """
        value = 0.0
        amplitude = 1.0
        frequency = self.base_frequency

        for octave in range(self.num_octaves):
            # Sample noise at current frequency
            # Multiply by frequency to get spatial coordinates in noise space
            sample_x = x * frequency
            sample_y = y * frequency

            # OpenSimplex noise returns values in [-1, 1]
            noise_value = self.noise.noise2(sample_x, sample_y)

            # Accumulate weighted noise
            value += noise_value * amplitude

            # Update for next octave
            amplitude *= PERSISTENCE  # Reduce amplitude (0.5 typical)
            frequency *= LACUNARITY   # Increase frequency (2.0 typical)

        # Normalize to [0, 1] range
        # The noise sum is approximately in [-amplitude_sum, +amplitude_sum]
        normalized = (value / self.amplitude_sum + 1.0) / 2.0

        # Clamp to ensure we stay in [0, 1] due to noise variations
        return np.clip(normalized, 0.0, 1.0)

    def get_density(self, x: float, y: float, time: float) -> float:
        """
        Sample atmospheric density at position (x, y) at given time.

        This is the key interface that propellers will use in Phase 2.
        The density field drifts horizontally at drift_velocity, simulating
        motion through a frozen turbulence pattern (Taylor's hypothesis).

        Args:
            x: Horizontal position in meters
            y: Vertical position in meters
            time: Simulation time in seconds

        Returns:
            Atmospheric density in kg/m³, in range [rho_min, rho_max]

        Example:
            >>> field = DensityField()
            >>> rho = field.get_density(100.0, 0.0, 5.0)  # 100m right, centerline, 5s
            >>> print(f"Density: {rho:.3f} kg/m³")
        """
        # Apply drift: shift the sampling position backward in time
        # This makes the pattern appear to move forward (left-to-right)
        x_drifted = x - self.drift_velocity * time

        # Sample the noise field
        noise_value = self._fbm_noise_2d(x_drifted, y)

        # Map [0, 1] noise to [rho_min, rho_max] density
        density = self.rho_min + noise_value * (self.rho_max - self.rho_min)

        return density

    def get_density_grid(
        self,
        x_array: np.ndarray,
        y_array: np.ndarray,
        time: float,
    ) -> np.ndarray:
        """
        Vectorized density sampling for efficient grid generation.

        Used for visualization - generates a 2D grid of density values.
        More efficient than calling get_density() in a loop.

        Args:
            x_array: 1D array of x coordinates (meters)
            y_array: 1D array of y coordinates (meters)
            time: Simulation time in seconds

        Returns:
            2D array of densities with shape (len(y_array), len(x_array))
            Values in kg/m³, in range [rho_min, rho_max]

        Example:
            >>> field = DensityField()
            >>> x = np.linspace(0, 1000, 100)
            >>> y = np.linspace(-100, 100, 40)
            >>> grid = field.get_density_grid(x, y, time=0.0)
            >>> print(grid.shape)  # (40, 100)
        """
        # Create 2D meshgrid
        X, Y = np.meshgrid(x_array, y_array)

        # Apply drift
        X_drifted = X - self.drift_velocity * time

        # Initialize output array
        density_grid = np.zeros_like(X)

        # Sample noise at each grid point
        # Note: Could be further optimized with vectorized noise library
        # (e.g., pyfastnoisesimd) but opensimplex is simpler for Phase 1
        for i in range(len(y_array)):
            for j in range(len(x_array)):
                noise_value = self._fbm_noise_2d(X_drifted[i, j], Y[i, j])
                density_grid[i, j] = (
                    self.rho_min + noise_value * (self.rho_max - self.rho_min)
                )

        return density_grid

    def get_statistics(self, grid: np.ndarray) -> dict:
        """
        Calculate statistical properties of a density grid.

        Useful for validation and debugging.

        Args:
            grid: 2D array of density values from get_density_grid()

        Returns:
            Dictionary with keys: 'mean', 'min', 'max', 'std'
        """
        return {
            'mean': np.mean(grid),
            'min': np.min(grid),
            'max': np.max(grid),
            'std': np.std(grid),
        }
