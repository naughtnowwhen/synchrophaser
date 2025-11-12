# Atmospheric Density Field Simulation - Phase 1

A physics-based atmospheric turbulence simulator for twin-propeller synchrophaser development. Phase 1 focuses on realistic density field generation using procedural noise with proper atmospheric parameters.

## Overview

This simulation generates smooth, time-varying atmospheric density fields that drift horizontally, representing an aircraft flying through turbulent air. The density variations will eventually create realistic disturbances for propeller dynamics and synchrophaser control systems.

### Key Features

- **Physics-based parameters**: Density range, wavelengths, and frequencies based on atmospheric turbulence theory
- **Real-time visualization**: Animated heatmap showing drifting density patterns at 30+ fps
- **Interactive controls**: Adjust wavelength, drift velocity, and complexity on the fly
- **Validation tools**: FFT analysis, spatial statistics, and drift verification
- **Modular design**: Clean interface (`get_density(x, y, t)`) ready for Phase 2 propeller integration

## Physics Foundation

### Atmospheric Parameters

- **Density range**: 1.15 to 1.30 kg/m³ (sea level: 1.225 kg/m³)
- **Spatial wavelengths**: 50-500 meters (atmospheric turbulence integral length scales)
- **Drift velocity**: 50 m/s (representing ~100 knots cruise speed)
- **Target frequencies**: 0.1-2 Hz (from Taylor's frozen turbulence: f = V/λ)

### Noise Generation

Uses **OpenSimplex noise** (patent-free) with **fractal Brownian motion**:
- 4-6 octaves for multi-scale turbulence
- Persistence: 0.5 (amplitude reduction per octave)
- Lacunarity: 2.0 (frequency multiplication per octave)

## Installation

### Requirements

- Python 3.8+
- numpy, matplotlib, scipy, opensimplex

### Setup

```bash
# Clone or download the repository
cd physicalEnv

# Install dependencies
pip install -r requirements.txt

# Make main.py executable (optional)
chmod +x main.py
```

## Usage

### Interactive Visualization (Default Mode)

```bash
python main.py
```

This opens an interactive window with:
- **Main view**: Drifting density field heatmap (red=dense, blue=light)
- **Controls**:
  - Wavelength slider: Adjust turbulence scale (50-500m)
  - Drift velocity slider: Adjust apparent wind speed (20-100 m/s)
  - Octaves slider: Adjust turbulence complexity (1-6)
  - Pause/Play button
  - Speed buttons: 0.5×, 1×, 2×, 4× playback speed
- **Info panel**: Current time, FPS, parameters
- **Statistics panel**: Mean, std dev, min/max density

### Validation Mode

Run physics validation tests:

```bash
python main.py --mode validate
```

Prints:
- Parameter summary
- Spatial statistics (mean, std, range, Gaussian test)
- Estimated wavelength from autocorrelation
- Drift verification (Taylor's hypothesis)

Option to export density snapshots as `.npz` files.

### FFT Analysis Mode

Analyze frequency content at a fixed point:

```bash
python main.py --mode fft --duration 60 --sample-rate 30
```

Generates:
- Time series plot of density variations
- Power spectrum with expected vs. observed peak frequency
- Validation that energy is in 0.1-2 Hz range

### Command-Line Options

```bash
python main.py [OPTIONS]

Options:
  --mode {visualize,validate,fft}  Operation mode (default: visualize)
  --wavelength W                   Turbulence wavelength in meters (default: 150)
  --drift V                        Drift velocity in m/s (default: 50)
  --octaves N                      Number of noise octaves (default: 4)
  --seed S                         Random seed (default: 42)
  --duration D                     Duration for FFT analysis (default: 60s)
  --sample-rate R                  Sample rate for FFT (default: 30 Hz)
```

### Examples

```bash
# Larger turbulence scale, slower drift
python main.py --wavelength 300 --drift 30

# More complex turbulence (more octaves)
python main.py --octaves 6

# Different random pattern
python main.py --seed 12345

# Quick FFT check
python main.py --mode fft --duration 30
```

## Code Structure

```
physicalEnv/
├── main.py              # Application entry point with CLI
├── density_field.py     # Core DensityField class
├── visualization.py     # Matplotlib animation and controls
├── validation.py        # FFT analysis, statistics, export
├── parameters.py        # Physics constants and defaults
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Key Components

#### DensityField Class

Core class providing the density field interface:

```python
from density_field import DensityField

# Create field with custom parameters
field = DensityField(
    wavelength=150.0,      # meters
    rho_min=1.15,          # kg/m³
    rho_max=1.30,          # kg/m³
    drift_velocity=50.0,   # m/s
    num_octaves=4,
    seed=42
)

# Sample density at any point in space-time
rho = field.get_density(x=100.0, y=0.0, time=5.0)

# Get full grid for visualization
import numpy as np
x_coords = np.linspace(0, 1000, 100)
y_coords = np.linspace(-100, 100, 40)
grid = field.get_density_grid(x_coords, y_coords, time=5.0)
```

#### Validation Tools

```python
from validation import DensityFieldValidator

# Frequency analysis at fixed point
result = DensityFieldValidator.frequency_analysis(
    field, x=500, y=0, duration=60.0, sample_rate=30.0
)
print(f"Peak frequency: {result['peak_frequency']:.3f} Hz")
print(f"Expected: {result['expected_frequency']:.3f} Hz")

# Spatial statistics
stats = DensityFieldValidator.spatial_analysis(grid, x_coords, y_coords)
print(f"Mean: {stats['mean']:.4f} kg/m³")

# Verify drift behavior
drift_check = DensityFieldValidator.verify_drift(field, x=500, y=0, dt=1.0)
print(f"Drift correct: {drift_check['is_drifting_correctly']}")
```

## Validation Results

The simulation has been validated against atmospheric turbulence theory:

✅ **Density range**: Values stay within [rho_min, rho_max] bounds
✅ **Spatial smoothness**: No discontinuities or artifacts
✅ **Drift behavior**: Patterns advect correctly (Taylor's hypothesis)
✅ **Frequency content**: FFT peak matches f = V/λ within ±20%
✅ **Statistical distribution**: Near-Gaussian density variations
✅ **Wavelength**: Autocorrelation matches specified dominant scale

## Future Integration (Phase 2+)

This density field is designed for seamless propeller integration:

```python
# Phase 2: Propeller samples local density
rho_local = density_field.get_density(propeller.x, propeller.y, sim_time)

# Aerodynamic torque scales with density
Q_aero = base_torque * (rho_local / rho_sealevel)

# This creates RPM variations that synchrophaser must compensate
```

The `get_density(x, y, t)` interface is stateless and can be called from multiple propellers simultaneously.

## Performance

- **Frame rate**: 30+ fps on modern hardware
- **Grid resolution**: 100×40 points (10m spacing)
- **Memory usage**: <100 MB
- **Real-time parameter changes**: Instant update without restart

### Optimization Notes

For higher performance in future phases, consider:
- `pyfastnoisesimd` for vectorized noise generation (10-100× speedup)
- Lower grid resolution for faster rendering
- Caching for repeated time queries

## Troubleshooting

### Visualization window not appearing

- Check if matplotlib backend supports GUI: `python -c "import matplotlib; print(matplotlib.get_backend())"`
- Try setting backend: `export MPLBACKEND=TkAgg` or `Qt5Agg`

### Low FPS

- Reduce grid resolution in `parameters.py`
- Decrease number of octaves (fewer = faster)
- Ensure no other CPU-intensive processes running

### Import errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

## References

Based on:
- "Building a Realistic Propeller Synchrophaser Physics Simulation" document
- Atmospheric turbulence integral length scales
- Taylor's frozen turbulence hypothesis
- Fractal Brownian motion noise generation

## License

Research/educational project. See parent repository for license details.

## Contact

For questions about synchrophaser simulation or Phase 2+ development, see project documentation.

---

**Phase 1 Complete** ✓
Next: Add propeller dynamics with governor control (Phase 2)
