# System Architecture - Phase 1

## Overview

The atmospheric density field simulation uses a modular, physics-based architecture designed for future extensibility. Each component has a clear responsibility and well-defined interfaces.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
│                          │                                   │
│                          ▼                                   │
│                      main.py                                 │
│                   (CLI Interface)                            │
│           ┌──────────┬────────┬──────────┐                  │
│           │          │        │          │                   │
│           ▼          ▼        ▼          ▼                   │
│     visualize    validate   fft      [future]               │
│           │          │        │                              │
└───────────┼──────────┼────────┼──────────────────────────────┘
            │          │        │
            ▼          ▼        ▼
    ┌────────────┐  ┌──────────────┐
    │ visualization│  │  validation  │
    │     .py      │  │     .py      │
    └──────┬───────┘  └──────┬───────┘
           │                 │
           └─────────┬───────┘
                     │
                     ▼
            ┌─────────────────┐
            │ density_field.py │ ◄── Core component
            │  DensityField    │
            └────────┬─────────┘
                     │
                     ├─► get_density(x, y, t) → ρ
                     ├─► get_density_grid(x[], y[], t) → ρ[][]
                     └─► get_statistics(grid) → stats
                     │
                     ▼
            ┌─────────────────┐
            │  opensimplex     │ ◄── External library
            │  (noise gen)     │
            └──────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  parameters.py   │ ◄── Physics constants
            └──────────────────┘
```

## Data Flow

### Visualization Mode

```
User → main.py → DensityFieldVisualizer
                       │
                       ├─► creates DensityField
                       │         │
                       │         ├─► init OpenSimplex(seed)
                       │         └─► calc base_frequency
                       │
                       └─► Animation Loop (30+ fps):
                             │
                             ├─► update simulation time
                             ├─► call get_density_grid(x, y, t)
                             │         │
                             │         └─► for each grid point:
                             │               ├─► apply drift: x' = x - V*t
                             │               ├─► compute fBm noise
                             │               │     └─► sum octaves with
                             │               │         persistence & lacunarity
                             │               └─► map to [ρ_min, ρ_max]
                             │
                             ├─► update matplotlib heatmap
                             ├─► compute statistics
                             └─► render to screen
```

### Validation Mode

```
User → main.py → DensityFieldValidator
                       │
                       ├─► create DensityField
                       │
                       ├─► spatial_analysis():
                       │     ├─► generate grid
                       │     ├─► compute statistics
                       │     └─► autocorrelation
                       │
                       ├─► verify_drift():
                       │     ├─► sample ρ(x, t)
                       │     ├─► sample ρ(x+V*dt, t+dt)
                       │     └─► compare (Taylor's hypothesis)
                       │
                       └─► print_validation_report()
```

### FFT Analysis Mode

```
User → main.py → DensityFieldValidator.frequency_analysis()
                       │
                       ├─► create time series:
                       │     └─► for t in [0, duration]:
                       │           └─► ρ(x_fixed, y_fixed, t)
                       │
                       ├─► compute power spectrum:
                       │     └─► scipy.signal.welch(ρ_series)
                       │
                       ├─► find peak frequency
                       ├─► compare to expected: f = V/λ
                       └─► plot time series & spectrum
```

## Class Structure

### DensityField Class

```python
class DensityField:
    # Instance variables
    wavelength: float           # Dominant turbulence scale (m)
    rho_min: float             # Min density (kg/m³)
    rho_max: float             # Max density (kg/m³)
    drift_velocity: float      # Apparent wind speed (m/s)
    num_octaves: int           # fBm octaves
    seed: int                  # Random seed
    noise: OpenSimplex         # Noise generator
    base_frequency: float      # 1/wavelength
    amplitude_sum: float       # Normalization factor

    # Public interface (stateless)
    get_density(x, y, t) → ρ
    get_density_grid(x[], y[], t) → ρ[][]
    get_statistics(grid) → dict

    # Private methods
    _fbm_noise_2d(x, y) → [0,1]
```

### DensityFieldVisualizer Class

```python
class DensityFieldVisualizer:
    # Instance variables
    density_field: DensityField
    sim_time: float
    is_paused: bool
    speed_multiplier: float
    fig, axes: matplotlib objects
    sliders: list[Slider]
    buttons: list[Button]

    # Public interface
    start(interval)
    stop()

    # Private methods
    _setup_figure()
    _update_frame(frame)
    _on_wavelength_change(val)
    _on_drift_change(val)
    _on_playpause(event)
    _on_speed_change(speed)
```

### DensityFieldValidator Class (static methods)

```python
class DensityFieldValidator:
    @staticmethod
    frequency_analysis(field, x, y, duration, sample_rate) → dict
    spatial_analysis(grid, x_coords, y_coords) → dict
    verify_drift(field, x, y, dt) → dict
    export_snapshot(grid, x, y, filename, format)
    print_validation_report(field, grid, x, y)
```

## Key Design Patterns

### 1. Stateless Interface
```python
# DensityField has no internal time state
# Can query any (x, y, t) independently
rho = field.get_density(x, y, t)

# Benefit: Easy to parallelize, no side effects
# Allows time-independent queries for Phase 2
```

### 2. Separation of Concerns
```
- density_field.py: Physics & noise generation
- visualization.py: GUI & animation
- validation.py: Analysis & verification
- parameters.py: Configuration
- main.py: User interface
```

### 3. Dependency Injection
```python
# Visualizer accepts existing DensityField
viz = DensityFieldVisualizer(density_field=field)

# Benefit: Can test visualization separately
# Can reuse same field in multiple visualizers
```

### 4. Factory Pattern (implicit)
```python
# main.py creates appropriate components based on mode
if mode == 'visualize':
    field = DensityField(...)
    viz = DensityFieldVisualizer(field)
elif mode == 'validate':
    field = DensityField(...)
    DensityFieldValidator.validate(field)
```

## Physics Implementation

### Fractal Brownian Motion (fBm)

```
ρ(x, y, t) = ρ_min + (ρ_max - ρ_min) * normalize(fBm(x', y'))

where:
  x' = x - V_drift * t           (drift transformation)

  fBm(x', y') = Σ A_i * noise(f_i * x', f_i * y')
                i=0 to N

  A_i = persistence^i            (amplitude per octave)
  f_i = base_freq * lacunarity^i (frequency per octave)

  normalize() maps [-sum(A_i), +sum(A_i)] to [0, 1]
```

### Drift Mechanism (Taylor's Frozen Turbulence)

```
The transformation x' = x - V*t makes patterns move:

At t=0: sample at x=100  →  x'=100    →  ρ(100, y, 0)
At t=1: sample at x=100  →  x'=50     →  ρ(50, y, 0)   (looks like pattern moved right)
At t=1: sample at x=150  →  x'=100    →  ρ(100, y, 0)  (same as above at t=0)

Result: Pattern appears to drift right at velocity V
```

## Performance Characteristics

### Time Complexity
- `get_density(x, y, t)`: O(n) where n = num_octaves (4-6)
- `get_density_grid(x[], y[], t)`: O(W * H * n) where W×H is grid size

### Space Complexity
- DensityField instance: O(1) - only stores parameters
- Grid storage: O(W * H) - typically 100×40 = 4000 floats ≈ 32 KB

### Bottlenecks
1. **Noise generation**: Each grid point requires n noise calls
   - Current: ~4000 points × 4 octaves = 16,000 noise calls per frame
   - Optimization: Use vectorized noise library (pyfastnoisesimd)

2. **Matplotlib rendering**: Drawing 4000 cells at 30 fps
   - Current: pcolormesh with 'auto' shading
   - Optimization: Reduce grid resolution or use blitting

## Extension Points for Phase 2

### Adding Propellers

```python
class Propeller:
    def __init__(self, x, y, density_field):
        self.x = x
        self.y = y
        self.field = density_field
        self.rpm = 2400.0  # nominal
        self.inertia = 5.0  # kg·m²

    def update(self, dt, sim_time):
        # Sample local density
        rho_local = self.field.get_density(self.x, self.y, sim_time)

        # Compute aerodynamic torque (scales with density)
        rho_ref = 1.225
        Q_aero = self.base_torque * (rho_local / rho_ref)

        # Integrate equation of motion
        # I * dω/dt = Q_engine - Q_aero
        # ... (governor control, dynamics)
```

### Visualization Enhancement

```python
# Add propeller markers to existing visualization
class DensityFieldVisualizer:
    def __init__(self, density_field, propellers=None):
        self.propellers = propellers or []

    def _update_frame(self, frame):
        # ... existing density field update ...

        # Add propeller markers
        for prop in self.propellers:
            self.ax_main.plot(prop.x, prop.y, 'ko', markersize=10)
```

## Testing Strategy

### Unit Tests (test_unit.py)
- Test individual methods in isolation
- Verify physics properties (range, drift, wavelength)
- Edge cases and boundary conditions

### Integration Tests (test_basic.py)
- Test component interactions
- End-to-end workflows
- Verify output correctness

### Validation Tests (main.py --mode validate)
- Physics-based verification
- Frequency analysis (FFT)
- Statistical properties

## Configuration Management

All physics parameters centralized in `parameters.py`:

```python
# Easy to tune for different scenarios
WAVELENGTH_DEFAULT = 150.0      # Light turbulence
# WAVELENGTH_DEFAULT = 300.0    # Heavy turbulence

DRIFT_VELOCITY_DEFAULT = 50.0   # 100 knots cruise
# DRIFT_VELOCITY_DEFAULT = 30.0  # 60 knots approach
```

## Future Architecture (Multi-Phase)

```
Phase 1: DensityField (COMPLETE)
           ↓
Phase 2: + Propeller dynamics
           ↓  calls get_density()
           ↓
Phase 3: + Governor control
           ↓  adjusts propeller pitch/fuel
           ↓
Phase 4: + Synchrophaser PLL
           ↓  coordinates propellers
           ↓
Full System: Density field → Propeller → Governor → Synchrophaser
```

## Conclusion

The architecture is:
- **Modular**: Clear component boundaries
- **Testable**: Each component tested independently
- **Extensible**: Ready for Phase 2 integration
- **Performant**: Meets 30+ fps target
- **Documented**: Comprehensive inline comments

All design decisions prioritize clean interfaces for future propeller integration while maintaining Phase 1 simplicity.
