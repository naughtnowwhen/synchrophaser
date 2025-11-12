"""
Real-time visualization of atmospheric density field.

Provides animated matplotlib display with interactive controls for parameter adjustment.
Shows drifting density patterns with colorbar and statistics overlay.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
import time

from density_field import DensityField
from parameters import (
    DOMAIN_WIDTH,
    DOMAIN_HEIGHT,
    GRID_RESOLUTION_X,
    GRID_RESOLUTION_Y,
    COLORMAP,
    TARGET_FPS,
    WAVELENGTH_MIN,
    WAVELENGTH_MAX,
    WAVELENGTH_DEFAULT,
    DRIFT_VELOCITY_MIN,
    DRIFT_VELOCITY_MAX,
    DRIFT_VELOCITY_DEFAULT,
    RHO_MIN_DEFAULT,
    RHO_MAX_DEFAULT,
    NUM_OCTAVES_MIN,
    NUM_OCTAVES_MAX,
    NUM_OCTAVES_DEFAULT,
)


class DensityFieldVisualizer:
    """
    Interactive real-time visualization of atmospheric density field.

    Features:
    - Animated heatmap showing drifting density patterns
    - Interactive sliders for parameter adjustment
    - Play/pause control
    - Speed multiplier control
    - FPS counter and statistics display
    - Placeholders for future propeller integration
    """

    def __init__(self, density_field: DensityField = None):
        """
        Initialize visualizer.

        Args:
            density_field: DensityField instance (creates default if None)
        """
        # Create density field if not provided
        self.density_field = density_field or DensityField()

        # Simulation state
        self.sim_time = 0.0
        self.is_paused = False
        self.speed_multiplier = 1.0
        self.last_update_time = time.time()
        self.fps_history = []

        # Create spatial grid
        self.x_coords = np.linspace(0, DOMAIN_WIDTH, GRID_RESOLUTION_X)
        self.y_coords = np.linspace(
            -DOMAIN_HEIGHT / 2, DOMAIN_HEIGHT / 2, GRID_RESOLUTION_Y
        )

        # Set up the figure and axes
        self._setup_figure()

        # Animation object (created when start() is called)
        self.animation = None

    def _setup_figure(self):
        """Create figure with main plot and control widgets."""
        # Create figure with specific layout
        self.fig = plt.figure(figsize=(14, 8))
        self.fig.suptitle(
            'Atmospheric Density Field - Phase 1',
            fontsize=14,
            fontweight='bold',
        )

        # Main density field plot
        self.ax_main = plt.subplot2grid((4, 3), (0, 0), colspan=2, rowspan=3)
        self.ax_main.set_xlabel('X Position (m)')
        self.ax_main.set_ylabel('Y Position (m)')
        self.ax_main.set_title('Density Field (drifting left-to-right)')

        # Initialize empty plot
        X, Y = np.meshgrid(self.x_coords, self.y_coords)
        initial_grid = self.density_field.get_density_grid(
            self.x_coords, self.y_coords, 0.0
        )

        self.im = self.ax_main.pcolormesh(
            X,
            Y,
            initial_grid,
            cmap=COLORMAP,
            shading='auto',
            vmin=self.density_field.rho_min,
            vmax=self.density_field.rho_max,
        )

        # Colorbar
        self.cbar = self.fig.colorbar(self.im, ax=self.ax_main)
        self.cbar.set_label('Density (kg/m³)', rotation=270, labelpad=20)

        # Info text box
        self.ax_info = plt.subplot2grid((4, 3), (0, 2), rowspan=2)
        self.ax_info.axis('off')
        self.info_text = self.ax_info.text(
            0.05, 0.95, '', transform=self.ax_info.transAxes,
            verticalalignment='top', fontfamily='monospace', fontsize=9
        )

        # Statistics text box
        self.ax_stats = plt.subplot2grid((4, 3), (2, 2), rowspan=1)
        self.ax_stats.axis('off')
        self.stats_text = self.ax_stats.text(
            0.05, 0.95, '', transform=self.ax_stats.transAxes,
            verticalalignment='top', fontfamily='monospace', fontsize=9
        )

        # Placeholder for future plots (time series, FFT, etc.)
        self.ax_placeholder = plt.subplot2grid((4, 3), (3, 0), colspan=2)
        self.ax_placeholder.text(
            0.5, 0.5, 'Future: Propeller RPM / Phase Error Time Series',
            ha='center', va='center', fontsize=10, style='italic', color='gray'
        )
        self.ax_placeholder.set_xticks([])
        self.ax_placeholder.set_yticks([])

        # Control widgets area
        self.ax_controls = plt.subplot2grid((4, 3), (3, 2))
        self.ax_controls.axis('off')

        # Create sliders
        slider_height = 0.03
        slider_spacing = 0.05

        # Wavelength slider
        self.ax_wavelength = plt.axes([0.15, 0.15, 0.3, slider_height])
        self.slider_wavelength = Slider(
            self.ax_wavelength,
            'Wavelength (m)',
            WAVELENGTH_MIN,
            WAVELENGTH_MAX,
            valinit=WAVELENGTH_DEFAULT,
            valstep=10.0,
        )
        self.slider_wavelength.on_changed(self._on_wavelength_change)

        # Drift velocity slider
        self.ax_drift = plt.axes([0.15, 0.15 - slider_spacing, 0.3, slider_height])
        self.slider_drift = Slider(
            self.ax_drift,
            'Drift (m/s)',
            DRIFT_VELOCITY_MIN,
            DRIFT_VELOCITY_MAX,
            valinit=DRIFT_VELOCITY_DEFAULT,
            valstep=5.0,
        )
        self.slider_drift.on_changed(self._on_drift_change)

        # Num octaves slider
        self.ax_octaves = plt.axes([0.15, 0.15 - 2 * slider_spacing, 0.3, slider_height])
        self.slider_octaves = Slider(
            self.ax_octaves,
            'Octaves',
            NUM_OCTAVES_MIN,
            NUM_OCTAVES_MAX,
            valinit=NUM_OCTAVES_DEFAULT,
            valstep=1,
        )
        self.slider_octaves.on_changed(self._on_octaves_change)

        # Play/Pause button
        self.ax_playpause = plt.axes([0.55, 0.15, 0.08, 0.04])
        self.btn_playpause = Button(self.ax_playpause, 'Pause')
        self.btn_playpause.on_clicked(self._on_playpause)

        # Speed buttons
        self.speed_buttons = []
        speeds = [0.5, 1.0, 2.0, 4.0]
        for i, speed in enumerate(speeds):
            ax_speed = plt.axes([0.55 + i * 0.06, 0.09, 0.05, 0.04])
            btn = Button(ax_speed, f'{speed}×')
            btn.on_clicked(lambda event, s=speed: self._on_speed_change(s))
            self.speed_buttons.append(btn)

        plt.tight_layout()

    def _on_wavelength_change(self, val):
        """Handle wavelength slider change."""
        self.density_field.wavelength = val
        self.density_field.base_frequency = 1.0 / val

    def _on_drift_change(self, val):
        """Handle drift velocity slider change."""
        self.density_field.drift_velocity = val

    def _on_octaves_change(self, val):
        """Handle octaves slider change."""
        new_octaves = int(val)
        self.density_field.num_octaves = new_octaves
        # Recalculate amplitude sum for normalization
        from parameters import PERSISTENCE
        self.density_field.amplitude_sum = sum(
            PERSISTENCE ** i for i in range(new_octaves)
        )

    def _on_playpause(self, event):
        """Toggle play/pause."""
        self.is_paused = not self.is_paused
        self.btn_playpause.label.set_text('Play' if self.is_paused else 'Pause')

    def _on_speed_change(self, speed):
        """Change simulation speed multiplier."""
        self.speed_multiplier = speed

    def _update_frame(self, frame):
        """
        Animation update function called for each frame.

        Args:
            frame: Frame number (not used, we track time internally)
        """
        # Calculate time step
        current_time = time.time()
        real_dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Update simulation time (unless paused)
        if not self.is_paused:
            self.sim_time += real_dt * self.speed_multiplier

        # Calculate FPS
        if real_dt > 0:
            fps = 1.0 / real_dt
            self.fps_history.append(fps)
            if len(self.fps_history) > 30:
                self.fps_history.pop(0)
            avg_fps = np.mean(self.fps_history)
        else:
            avg_fps = 0.0

        # Generate new density grid
        density_grid = self.density_field.get_density_grid(
            self.x_coords, self.y_coords, self.sim_time
        )

        # Update plot
        self.im.set_array(density_grid.ravel())

        # Update colorbar limits if density range changed
        self.im.set_clim(
            self.density_field.rho_min,
            self.density_field.rho_max,
        )

        # Calculate statistics
        mean_rho = np.mean(density_grid)
        std_rho = np.std(density_grid)
        min_rho = np.min(density_grid)
        max_rho = np.max(density_grid)

        # Update info text
        expected_freq = (
            self.density_field.drift_velocity / self.density_field.wavelength
        )
        info_str = (
            f"Time: {self.sim_time:.2f} s\n"
            f"FPS: {avg_fps:.1f}\n"
            f"Speed: {self.speed_multiplier}×\n"
            f"Status: {'PAUSED' if self.is_paused else 'RUNNING'}\n\n"
            f"Wavelength: {self.density_field.wavelength:.0f} m\n"
            f"Drift: {self.density_field.drift_velocity:.0f} m/s\n"
            f"Expected f: {expected_freq:.3f} Hz\n"
            f"Octaves: {self.density_field.num_octaves}\n"
        )
        self.info_text.set_text(info_str)

        # Update statistics text
        stats_str = (
            f"Field Statistics:\n"
            f"Mean: {mean_rho:.4f} kg/m³\n"
            f"Std:  {std_rho:.4f} kg/m³\n"
            f"Min:  {min_rho:.4f} kg/m³\n"
            f"Max:  {max_rho:.4f} kg/m³\n"
        )
        self.stats_text.set_text(stats_str)

        return [self.im, self.info_text, self.stats_text]

    def start(self, interval: int = None):
        """
        Start the animation.

        Args:
            interval: Update interval in milliseconds (default: 1000/TARGET_FPS)
        """
        if interval is None:
            interval = int(1000 / TARGET_FPS)

        self.last_update_time = time.time()

        self.animation = FuncAnimation(
            self.fig,
            self._update_frame,
            interval=interval,
            blit=False,  # Set to False for better widget compatibility
            cache_frame_data=False,
        )

        plt.show()

    def stop(self):
        """Stop the animation."""
        if self.animation:
            self.animation.event_source.stop()
