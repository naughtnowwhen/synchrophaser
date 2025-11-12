#!/usr/bin/env python3
"""
Main entry point for atmospheric density field simulation.

Phase 1: Density field visualization with physics-based parameters
Phase 2: Propeller dynamics with governor control

Usage:
    python main.py [--mode MODE] [--wavelength W] [--drift V] [--seed S]

Modes:
    propeller: Propeller with density field (Phase 2 - default)
    visualize: Density field only (Phase 1)
    validate: Run validation tests and print report
    fft: Perform frequency analysis at a fixed point
"""

import argparse
import sys
import numpy as np

from density_field import DensityField
from visualization import DensityFieldVisualizer
from visualization_phase2 import PropellerVisualizer
from propeller import Propeller
from validation import DensityFieldValidator
from parameters import (
    WAVELENGTH_DEFAULT,
    DRIFT_VELOCITY_DEFAULT,
    NUM_OCTAVES_DEFAULT,
    DEFAULT_SEED,
    DOMAIN_WIDTH,
    DOMAIN_HEIGHT,
    GRID_RESOLUTION_X,
    GRID_RESOLUTION_Y,
)


def run_visualization(args):
    """Run interactive visualization mode."""
    print("=" * 60)
    print("ATMOSPHERIC DENSITY FIELD - PHASE 1")
    print("=" * 60)
    print("\nStarting interactive visualization...")
    print("Controls:")
    print("  - Wavelength slider: Adjust turbulence scale (50-500m)")
    print("  - Drift slider: Adjust apparent wind speed (20-100 m/s)")
    print("  - Octaves slider: Adjust turbulence complexity (1-6)")
    print("  - Pause/Play button: Pause or resume animation")
    print("  - Speed buttons: Change playback speed (0.5×, 1×, 2×, 4×)")
    print("\nClose the window to exit.")
    print("=" * 60)

    # Create density field with command-line parameters
    field = DensityField(
        wavelength=args.wavelength,
        drift_velocity=args.drift,
        num_octaves=args.octaves,
        seed=args.seed,
    )

    # Create and start visualizer
    viz = DensityFieldVisualizer(field)
    viz.start()


def run_propeller_visualization(args):
    """Run interactive propeller visualization mode (Phase 2)."""
    print("=" * 60)
    print("PROPELLER DYNAMICS WITH DENSITY FIELD - PHASE 2")
    print("=" * 60)
    print("\nStarting propeller simulation...")
    print("Features:")
    print("  - Propeller responding to density variations")
    print("  - Vertical RPM speedometer (green = nominal)")
    print("  - Time-series graphs for density and RPM")
    print("  - Governor attempting to maintain constant speed")
    print("\nControls:")
    print("  - Wavelength slider: Adjust turbulence scale")
    print("  - Drift slider: Adjust wind speed")
    print("  - Octaves slider: Adjust turbulence complexity")
    print("  - Pause/Play and speed controls")
    print("\nClose the window to exit.")
    print("=" * 60)

    # Create density field with command-line parameters
    field = DensityField(
        wavelength=args.wavelength,
        drift_velocity=args.drift,
        num_octaves=args.octaves,
        seed=args.seed,
    )

    # Create propeller
    propeller = Propeller()

    # Create and start visualizer
    viz = PropellerVisualizer(field, propeller)
    viz.start()


def run_validation(args):
    """Run validation tests and print report."""
    print("\n" + "=" * 60)
    print("RUNNING VALIDATION TESTS")
    print("=" * 60)

    # Create density field
    field = DensityField(
        wavelength=args.wavelength,
        drift_velocity=args.drift,
        num_octaves=args.octaves,
        seed=args.seed,
    )

    # Generate a density grid
    x_coords = np.linspace(0, DOMAIN_WIDTH, GRID_RESOLUTION_X)
    y_coords = np.linspace(-DOMAIN_HEIGHT / 2, DOMAIN_HEIGHT / 2, GRID_RESOLUTION_Y)
    density_grid = field.get_density_grid(x_coords, y_coords, time=0.0)

    # Print validation report
    DensityFieldValidator.print_validation_report(
        field, density_grid, x_coords, y_coords
    )

    # Ask if user wants to export snapshot
    response = input("\nExport density snapshot? (y/n): ").lower().strip()
    if response == 'y':
        filename = input("Enter filename (without extension): ").strip()
        if filename:
            DensityFieldValidator.export_snapshot(
                density_grid, x_coords, y_coords, filename, file_format='npz'
            )
            print(f"Saved to {filename}.npz")


def run_fft_analysis(args):
    """Run FFT analysis at a fixed point."""
    print("\n" + "=" * 60)
    print("FREQUENCY ANALYSIS")
    print("=" * 60)

    # Create density field
    field = DensityField(
        wavelength=args.wavelength,
        drift_velocity=args.drift,
        num_octaves=args.octaves,
        seed=args.seed,
    )

    print(f"\nSampling density at fixed point: x=500m, y=0m")
    print(f"Duration: {args.duration}s at {args.sample_rate} Hz")
    print("Computing FFT...\n")

    # Run frequency analysis
    result = DensityFieldValidator.frequency_analysis(
        field,
        x=500.0,
        y=0.0,
        duration=args.duration,
        sample_rate=args.sample_rate,
    )

    print(f"Expected frequency (V/λ): {result['expected_frequency']:.4f} Hz")
    print(f"Peak frequency (FFT): {result['peak_frequency']:.4f} Hz")
    error_pct = abs(
        result['peak_frequency'] - result['expected_frequency']
    ) / result['expected_frequency'] * 100
    print(f"Error: {error_pct:.1f}%")

    # Show if within expected range
    from parameters import FREQUENCY_MIN, FREQUENCY_MAX
    in_range = FREQUENCY_MIN <= result['peak_frequency'] <= FREQUENCY_MAX
    print(f"In expected range [{FREQUENCY_MIN}, {FREQUENCY_MAX}] Hz: {in_range}")

    # Plot FFT if matplotlib is available
    try:
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Time series
        ax1.plot(result['times'], result['density'])
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Density (kg/m³)')
        ax1.set_title('Density Time Series at Fixed Point (x=500m, y=0m)')
        ax1.grid(True, alpha=0.3)

        # Power spectrum
        ax2.plot(result['frequencies'], result['power'])
        ax2.axvline(
            result['expected_frequency'],
            color='r',
            linestyle='--',
            label=f'Expected: {result["expected_frequency"]:.3f} Hz',
        )
        ax2.axvline(
            result['peak_frequency'],
            color='g',
            linestyle='--',
            label=f'Peak: {result["peak_frequency"]:.3f} Hz',
        )
        ax2.set_xlabel('Frequency (Hz)')
        ax2.set_ylabel('Power Spectral Density')
        ax2.set_title('Frequency Content')
        ax2.set_xlim(0, 2.0)
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        plt.tight_layout()
        plt.show()

    except ImportError:
        print("\nNote: Install matplotlib to see plots")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Atmospheric Density Field Simulation - Phase 2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--mode',
        choices=['propeller', 'visualize', 'validate', 'fft'],
        default='propeller',
        help='Operation mode (default: propeller)',
    )

    parser.add_argument(
        '--wavelength',
        type=float,
        default=WAVELENGTH_DEFAULT,
        help=f'Turbulence wavelength in meters (default: {WAVELENGTH_DEFAULT})',
    )

    parser.add_argument(
        '--drift',
        type=float,
        default=DRIFT_VELOCITY_DEFAULT,
        help=f'Drift velocity in m/s (default: {DRIFT_VELOCITY_DEFAULT})',
    )

    parser.add_argument(
        '--octaves',
        type=int,
        default=NUM_OCTAVES_DEFAULT,
        help=f'Number of noise octaves (default: {NUM_OCTAVES_DEFAULT})',
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=DEFAULT_SEED,
        help=f'Random seed (default: {DEFAULT_SEED})',
    )

    # FFT-specific arguments
    parser.add_argument(
        '--duration',
        type=float,
        default=60.0,
        help='Duration for FFT analysis in seconds (default: 60)',
    )

    parser.add_argument(
        '--sample-rate',
        type=float,
        default=30.0,
        help='Sample rate for FFT analysis in Hz (default: 30)',
    )

    args = parser.parse_args()

    # Dispatch to appropriate mode
    try:
        if args.mode == 'propeller':
            run_propeller_visualization(args)
        elif args.mode == 'visualize':
            run_visualization(args)
        elif args.mode == 'validate':
            run_validation(args)
        elif args.mode == 'fft':
            run_fft_analysis(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
