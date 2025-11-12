"""
Real-time visualization of atmospheric density field with propeller dynamics.

Phase 2: Adds propeller visualization, speedometer gauge, and time-series plots.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from collections import deque
import time

from density_field import DensityField
from propeller import Propeller
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
    NUM_OCTAVES_MIN,
    NUM_OCTAVES_MAX,
    NUM_OCTAVES_DEFAULT,
    PROPELLER_RADIUS,
    RPM_MIN_DISPLAY,
    RPM_MAX_DISPLAY,
    PROPELLER_RPM_NOMINAL,
    TIMESERIES_WINDOW,
    TIMESERIES_UPDATE_RATE,
)


class PropellerVisualizer:
    """
    Interactive visualization with propeller dynamics.

    Features:
    - Animated density field heatmap
    - Propeller position marker with blades
    - Vertical speedometer gauge showing RPM
    - Time-series plots for density and RPM history
    - Interactive controls for parameters
    """

    def __init__(
        self,
        density_field: DensityField = None,
        propeller: Propeller = None,
    ):
        """
        Initialize visualizer with density field and propeller.

        Args:
            density_field: DensityField instance (creates default if None)
            propeller: Propeller instance (creates default if None)
        """
        # Create components if not provided
        self.density_field = density_field or DensityField()
        self.propeller = propeller or Propeller()

        # Simulation state
        self.sim_time = 0.0
        self.is_paused = False
        self.speed_multiplier = 1.0
        self.last_update_time = time.time()
        self.fps_history = []

        # Time-series data storage
        self.history_time = deque(maxlen=int(TIMESERIES_WINDOW * TIMESERIES_UPDATE_RATE))
        self.history_rpm = deque(maxlen=int(TIMESERIES_WINDOW * TIMESERIES_UPDATE_RATE))
        self.history_density = deque(maxlen=int(TIMESERIES_WINDOW * TIMESERIES_UPDATE_RATE))
        self.last_history_update = 0.0
        self.history_update_interval = 1.0 / TIMESERIES_UPDATE_RATE

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
        """Create figure with all visualization elements."""
        # Create figure with larger size for additional plots
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle(
            'Atmospheric Density Field with Propeller - Phase 2',
            fontsize=14,
            fontweight='bold',
        )

        # Layout:
        # [0,0-1] Main density field (2 cols)    [0,2] Speedometer
        # [1,0-1] Time-series plot (2 cols)      [1,2] Info panel
        # [2,0-1] Controls/sliders (2 cols)      [2,2] Stats panel

        # Main density field plot
        self.ax_main = plt.subplot2grid((3, 3), (0, 0), colspan=2)
        self.ax_main.set_xlabel('X Position (m)')
        self.ax_main.set_ylabel('Y Position (m)')
        self.ax_main.set_title('Density Field with Propeller')
        self.ax_main.set_xlim(0, DOMAIN_WIDTH)
        self.ax_main.set_ylim(-DOMAIN_HEIGHT / 2, DOMAIN_HEIGHT / 2)

        # Initialize density field plot
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

        # Propeller marker on main plot
        self.propeller_circle = Circle(
            (self.propeller.x, self.propeller.y),
            PROPELLER_RADIUS * 3,
            color='black',
            fill=True,
            zorder=10,
        )
        self.ax_main.add_patch(self.propeller_circle)

        # Propeller blades (two perpendicular lines)
        blade_len = PROPELLER_RADIUS * 5
        self.blade1 = self.ax_main.plot(
            [self.propeller.x, self.propeller.x],
            [self.propeller.y - blade_len, self.propeller.y + blade_len],
            'k-', linewidth=3, zorder=11
        )[0]
        self.blade2 = self.ax_main.plot(
            [self.propeller.x - blade_len * 0.3, self.propeller.x + blade_len * 0.3],
            [self.propeller.y, self.propeller.y],
            'k-', linewidth=3, zorder=11
        )[0]

        # Vertical speedometer (right side, top)
        self.ax_speedometer = plt.subplot2grid((3, 3), (0, 2))
        self._setup_speedometer()

        # Time-series plot (bottom, spanning 2 columns)
        self.ax_timeseries = plt.subplot2grid((3, 3), (1, 0), colspan=2)
        self._setup_timeseries()

        # Info text panel
        self.ax_info = plt.subplot2grid((3, 3), (1, 2))
        self.ax_info.axis('off')
        self.info_text = self.ax_info.text(
            0.05, 0.95, '', transform=self.ax_info.transAxes,
            verticalalignment='top', fontfamily='monospace', fontsize=8
        )

        # Statistics panel
        self.ax_stats = plt.subplot2grid((3, 3), (2, 2))
        self.ax_stats.axis('off')
        self.stats_text = self.ax_stats.text(
            0.05, 0.95, '', transform=self.ax_stats.transAxes,
            verticalalignment='top', fontfamily='monospace', fontsize=8
        )

        # Control widgets
        self._setup_controls()

        plt.tight_layout()

    def _setup_speedometer(self):
        """Create vertical RPM speedometer gauge."""
        self.ax_speedometer.set_xlim(0, 1)
        self.ax_speedometer.set_ylim(RPM_MIN_DISPLAY, RPM_MAX_DISPLAY)
        self.ax_speedometer.set_ylabel('RPM', fontweight='bold')
        self.ax_speedometer.set_title('Propeller Speed')
        self.ax_speedometer.set_xticks([])
        self.ax_speedometer.yaxis.tick_right()
        self.ax_speedometer.yaxis.set_label_position('right')

        # Draw gauge background zones
        # Green zone around nominal
        green_height = 50
        self.ax_speedometer.axhspan(
            PROPELLER_RPM_NOMINAL - green_height,
            PROPELLER_RPM_NOMINAL + green_height,
            color='lightgreen', alpha=0.3, zorder=1
        )
        # Yellow zones
        self.ax_speedometer.axhspan(
            RPM_MIN_DISPLAY,
            PROPELLER_RPM_NOMINAL - green_height,
            color='yellow', alpha=0.2, zorder=1
        )
        self.ax_speedometer.axhspan(
            PROPELLER_RPM_NOMINAL + green_height,
            RPM_MAX_DISPLAY,
            color='yellow', alpha=0.2, zorder=1
        )

        # Nominal RPM line
        self.ax_speedometer.axhline(
            PROPELLER_RPM_NOMINAL,
            color='black', linestyle='--', linewidth=2, zorder=2
        )

        # Current RPM bar
        self.rpm_bar = Rectangle(
            (0.2, RPM_MIN_DISPLAY),
            0.6,
            PROPELLER_RPM_NOMINAL - RPM_MIN_DISPLAY,
            facecolor='blue', edgecolor='black', linewidth=2, zorder=3
        )
        self.ax_speedometer.add_patch(self.rpm_bar)

        # RPM value text
        self.rpm_text = self.ax_speedometer.text(
            0.5, PROPELLER_RPM_NOMINAL, f'{PROPELLER_RPM_NOMINAL:.0f}',
            ha='center', va='center', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
            zorder=4
        )

    def _setup_timeseries(self):
        """Create time-series plot for density and RPM."""
        self.ax_timeseries.set_xlabel('Time (s)')
        self.ax_timeseries.set_ylabel('Density (kg/m³)', color='blue')
        self.ax_timeseries.tick_params(axis='y', labelcolor='blue')
        self.ax_timeseries.set_title('Propeller Environment History')
        self.ax_timeseries.grid(True, alpha=0.3)

        # Initialize density line
        self.line_density, = self.ax_timeseries.plot(
            [], [], 'b-', linewidth=2, label='Local Density'
        )

        # Create second y-axis for RPM
        self.ax_rpm = self.ax_timeseries.twinx()
        self.ax_rpm.set_ylabel('RPM', color='green')
        self.ax_rpm.tick_params(axis='y', labelcolor='green')

        # Initialize RPM line
        self.line_rpm, = self.ax_rpm.plot(
            [], [], 'g-', linewidth=2, label='Propeller RPM'
        )

        # Add legends
        lines = [self.line_density, self.line_rpm]
        labels = [l.get_label() for l in lines]
        self.ax_timeseries.legend(lines, labels, loc='upper left')

    def _setup_controls(self):
        """Create control sliders and buttons."""
        # Slider area at bottom
        slider_height = 0.02
        slider_spacing = 0.04

        # Wavelength slider
        self.ax_wavelength = plt.axes([0.15, 0.08, 0.3, slider_height])
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
        self.ax_drift = plt.axes([0.15, 0.08 - slider_spacing, 0.3, slider_height])
        self.slider_drift = Slider(
            self.ax_drift,
            'Drift (m/s)',
            DRIFT_VELOCITY_MIN,
            DRIFT_VELOCITY_MAX,
            valinit=DRIFT_VELOCITY_DEFAULT,
            valstep=5.0,
        )
        self.slider_drift.on_changed(self._on_drift_change)

        # Octaves slider
        self.ax_octaves = plt.axes([0.15, 0.08 - 2 * slider_spacing, 0.3, slider_height])
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
        self.ax_playpause = plt.axes([0.55, 0.06, 0.08, 0.03])
        self.btn_playpause = Button(self.ax_playpause, 'Pause')
        self.btn_playpause.on_clicked(self._on_playpause)

        # Speed buttons
        self.speed_buttons = []
        speeds = [0.5, 1.0, 2.0, 4.0]
        for i, speed in enumerate(speeds):
            ax_speed = plt.axes([0.55 + i * 0.06, 0.02, 0.05, 0.03])
            btn = Button(ax_speed, f'{speed}×')
            btn.on_clicked(lambda event, s=speed: self._on_speed_change(s))
            self.speed_buttons.append(btn)

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
        """Animation update function."""
        # Calculate time step
        current_time = time.time()
        real_dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Update simulation time (unless paused)
        if not self.is_paused:
            sim_dt = real_dt * self.speed_multiplier
            self.sim_time += sim_dt

            # Update propeller state
            self.propeller.update(sim_dt, self.sim_time, self.density_field)

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

        # Update density field plot
        self.im.set_array(density_grid.ravel())
        self.im.set_clim(self.density_field.rho_min, self.density_field.rho_max)

        # Update speedometer
        self._update_speedometer()

        # Update time-series history
        if self.sim_time - self.last_history_update >= self.history_update_interval:
            self.history_time.append(self.sim_time)
            self.history_rpm.append(self.propeller.rpm)
            self.history_density.append(self.propeller.rho_local)
            self.last_history_update = self.sim_time

        # Update time-series plot
        self._update_timeseries()

        # Update info panel
        self._update_info_panel(avg_fps)

        # Update statistics panel
        self._update_stats_panel(density_grid)

        return [self.im, self.rpm_bar, self.line_density, self.line_rpm]

    def _update_speedometer(self):
        """Update RPM speedometer bar and text."""
        current_rpm = self.propeller.rpm

        # Update bar height
        bar_height = current_rpm - RPM_MIN_DISPLAY
        self.rpm_bar.set_height(max(0, bar_height))

        # Color based on deviation from nominal
        rpm_error = abs(current_rpm - PROPELLER_RPM_NOMINAL)
        if rpm_error < 50:
            color = 'green'
        elif rpm_error < 100:
            color = 'yellow'
        else:
            color = 'red'
        self.rpm_bar.set_facecolor(color)

        # Update text
        self.rpm_text.set_position((0.5, current_rpm))
        self.rpm_text.set_text(f'{current_rpm:.0f}')

    def _update_timeseries(self):
        """Update time-series plot with new data."""
        if len(self.history_time) > 0:
            times = list(self.history_time)
            densities = list(self.history_density)
            rpms = list(self.history_rpm)

            # Update density line
            self.line_density.set_data(times, densities)

            # Update RPM line
            self.line_rpm.set_data(times, rpms)

            # Update x-axis limits (rolling window)
            if times[-1] > TIMESERIES_WINDOW:
                self.ax_timeseries.set_xlim(
                    times[-1] - TIMESERIES_WINDOW,
                    times[-1]
                )
            else:
                self.ax_timeseries.set_xlim(0, max(TIMESERIES_WINDOW, times[-1]))

            # Update y-axis limits
            if len(densities) > 1:
                d_min, d_max = min(densities), max(densities)
                d_margin = (d_max - d_min) * 0.1
                self.ax_timeseries.set_ylim(d_min - d_margin, d_max + d_margin)

            if len(rpms) > 1:
                r_min, r_max = min(rpms), max(rpms)
                r_margin = (r_max - r_min) * 0.1
                self.ax_rpm.set_ylim(
                    max(RPM_MIN_DISPLAY, r_min - r_margin),
                    min(RPM_MAX_DISPLAY, r_max + r_margin)
                )

    def _update_info_panel(self, avg_fps):
        """Update info text panel."""
        state = self.propeller.get_state()
        info_str = (
            f"Time: {self.sim_time:.2f} s\n"
            f"FPS: {avg_fps:.1f}\n"
            f"Speed: {self.speed_multiplier}×\n"
            f"Status: {'PAUSED' if self.is_paused else 'RUNNING'}\n\n"
            f"--- Propeller ---\n"
            f"RPM: {state['rpm']:.1f}\n"
            f"Target: {self.propeller.rpm_nominal:.0f}\n"
            f"Error: {state['rpm_error']:.1f}\n\n"
            f"--- Torques ---\n"
            f"Engine: {state['q_engine']:.1f} Nm\n"
            f"Aero: {state['q_aero']:.1f} Nm\n"
            f"Net: {state['q_net']:.1f} Nm\n"
        )
        self.info_text.set_text(info_str)

    def _update_stats_panel(self, density_grid):
        """Update statistics panel."""
        mean_rho = np.mean(density_grid)
        std_rho = np.std(density_grid)
        min_rho = np.min(density_grid)
        max_rho = np.max(density_grid)

        stats_str = (
            f"Field Statistics:\n"
            f"Mean: {mean_rho:.4f} kg/m³\n"
            f"Std:  {std_rho:.4f} kg/m³\n"
            f"Min:  {min_rho:.4f} kg/m³\n"
            f"Max:  {max_rho:.4f} kg/m³\n\n"
            f"At Propeller:\n"
            f"ρ: {self.propeller.rho_local:.4f} kg/m³\n"
        )
        self.stats_text.set_text(stats_str)

    def start(self, interval: int = None):
        """Start the animation."""
        if interval is None:
            interval = int(1000 / TARGET_FPS)

        self.last_update_time = time.time()

        self.animation = FuncAnimation(
            self.fig,
            self._update_frame,
            interval=interval,
            blit=False,
            cache_frame_data=False,
        )

        plt.show()

    def stop(self):
        """Stop the animation."""
        if self.animation:
            self.animation.event_source.stop()
