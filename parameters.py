"""
Physics parameters and constants for atmospheric density field simulation.

Based on atmospheric turbulence theory and aircraft cruise conditions.
See: "Building a Realistic Propeller Synchrophaser Physics Simulation"
"""

# Atmospheric density parameters (kg/m³)
RHO_SEA_LEVEL = 1.225  # Standard sea level density
RHO_MIN_DEFAULT = 1.15  # Lower bound for density variations
RHO_MAX_DEFAULT = 1.30  # Upper bound for density variations

# Turbulence spatial scales (meters)
# Based on atmospheric turbulence integral length scales
WAVELENGTH_MIN = 50.0   # Minimum turbulence wavelength
WAVELENGTH_MAX = 500.0  # Maximum turbulence wavelength
WAVELENGTH_DEFAULT = 150.0  # Default dominant scale

# Aircraft/wind parameters
DRIFT_VELOCITY_DEFAULT = 50.0  # m/s (~100 knots cruise speed)
DRIFT_VELOCITY_MIN = 20.0      # m/s (~40 knots)
DRIFT_VELOCITY_MAX = 100.0     # m/s (~200 knots)

# Noise generation parameters
NUM_OCTAVES_DEFAULT = 4  # Number of fractal noise layers
NUM_OCTAVES_MIN = 1
NUM_OCTAVES_MAX = 6
PERSISTENCE = 0.5  # Amplitude reduction per octave (standard fBm)
LACUNARITY = 2.0   # Frequency multiplication per octave (standard fBm)

# Visualization domain (meters)
DOMAIN_WIDTH = 1000.0   # Horizontal extent
DOMAIN_HEIGHT = 200.0   # Vertical extent (±100m from centerline)
GRID_RESOLUTION_X = 100  # Number of grid points horizontally
GRID_RESOLUTION_Y = 40   # Number of grid points vertically

# Temporal parameters
TARGET_FPS = 30  # Animation frame rate
SPEED_MULTIPLIERS = [0.5, 1.0, 2.0, 4.0]  # Available playback speeds

# Frequency range for validation (Hz)
# Calculated from Taylor's frozen turbulence: f = V/λ
# At V=50 m/s and λ=150m: f ≈ 0.33 Hz
FREQUENCY_MIN = 0.1  # Hz
FREQUENCY_MAX = 2.0  # Hz

# Random seed for reproducibility
DEFAULT_SEED = 42

# Color scheme for visualization
COLORMAP = 'RdYlBu_r'  # Red=dense, Blue=light (intuitive for "thick/thin" air)

# ============================================================================
# PHASE 2: PROPELLER PARAMETERS
# ============================================================================

# Propeller positioning
PROPELLER_X_DEFAULT = 900.0  # meters (right side of domain)
PROPELLER_Y_DEFAULT = 0.0    # meters (centerline)

# Propeller dynamics
PROPELLER_INERTIA = 8.0      # kg·m² (rotational inertia)
PROPELLER_RADIUS = 1.5       # meters (for visualization)
PROPELLER_RPM_NOMINAL = 2400.0  # Target RPM (typical for aircraft)

# RPM display range for speedometer
RPM_MIN_DISPLAY = 2200.0     # Lower bound for gauge
RPM_MAX_DISPLAY = 2600.0     # Upper bound for gauge

# Aerodynamic model (simplified)
# Q_aero = K_AERO * ρ * ω²
# This gives torque proportional to density and speed squared
# At nominal: Q_aero ≈ Q_base when ρ = 1.225, ω = 251.3 rad/s (2400 RPM)
# K_AERO = Q_base / (ρ * ω²) = 900 / (1.225 * 251.3²) ≈ 0.0116
K_AERO = 0.0116  # Aerodynamic torque coefficient (Nm·s²/rad²)

# Governor control
# Simple proportional controller: Q_engine = Q_base + K_P * (ω_target - ω)
GOVERNOR_K_P = 50.0          # Proportional gain (Nm·s/rad)
GOVERNOR_BASE_TORQUE = 900.0  # Base engine torque (Nm) at nominal density

# Time-series plot parameters
TIMESERIES_WINDOW = 30.0     # seconds (rolling window duration)
TIMESERIES_UPDATE_RATE = 10  # Hz (how often to add points to history)
