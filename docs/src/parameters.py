"""
Physics parameters and constants for atmospheric density field simulation.

Based on atmospheric turbulence theory and aircraft cruise conditions.
See: "Building a Realistic Propeller Synchrophaser Physics Simulation"
"""

# Atmospheric density parameters (kg/m³)
RHO_SEA_LEVEL = 1.225  # Standard sea level density
RHO_MIN_DEFAULT = 1.08  # Lower bound for density variations (MORE DRAMATIC!)
RHO_MAX_DEFAULT = 1.37  # Upper bound for density variations (MORE DRAMATIC!)

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

# Twin propeller setup (Phase 3)
PROPELLER_LEFT_Y = -60.0     # meters (below centerline)
PROPELLER_RIGHT_Y = +60.0    # meters (above centerline)

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

# ============================================================================
# PHASE 3: SYNCHROPHASER PARAMETERS
# ============================================================================

# Synchrophaser control (PID controller - Proportional-Integral-Derivative)
# Now uses TRUE PHASE error from actual blade positions!
# The synchrophaser minimizes phase difference: φ_error = φ_main - φ_follower
# Control output adjusts follower's RPM setpoint

# CONSERVATIVE GAINS to prevent overshoot and oscillation
SYNCHRO_K_P = 1.0            # Proportional gain (was 15.0, too aggressive!)
SYNCHRO_K_I = 0.1            # Integral gain (was 2.0, too aggressive!)
SYNCHRO_K_D = 0.5            # Derivative gain (was 3.0, amplifies noise!)

# Integrator anti-windup limits
SYNCHRO_INTEGRATOR_MIN = -100.0  # RPM
SYNCHRO_INTEGRATOR_MAX = +100.0  # RPM

# Phase error normalization (radians → RPM correction)
SYNCHRO_PHASE_SCALE = 30.0   # Scale factor for phase→RPM conversion (reduced from 50)

# Advanced control features to prevent overshoot/oscillation
SYNCHRO_DERIVATIVE_FILTER_ALPHA = 0.3  # Low-pass filter for derivative (0=no filter, 1=no smoothing) - increased for faster response
SYNCHRO_DEADBAND = 0.01         # Don't correct errors below this (radians, ~0.6°)
SYNCHRO_RATE_LIMIT = 20.0       # Max RPM/sec change in correction (prevents jumps) - increased for faster settling (2x original)

# Test mode parameters
TEST_MODE_DURATION = 60.0    # seconds per test phase (off/on)
TEST_MODE_SAMPLE_RATE = 10   # Hz (measurement frequency)
