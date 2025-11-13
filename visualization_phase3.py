"""
Real-time visualization of twin propellers with synchrophaser control.

Phase 3: Twin propellers with PLL-based synchrophaser, toggle control, and test mode.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
from matplotlib.patches import Circle
from collections import deque
import time

from density_field import DensityField
from propeller import Propeller
from synchrophaser import Synchrophaser, SynchrophaserTester
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
    TEST_MODE_DURATION,
)


class TwinPropellerVisualizer:
    """
    Interactive visualization with twin propellers and synchrophaser.

    Features:
    - Two vertically separated propellers
    - Time-series showing both RPM traces
    - Synchrophaser toggle (ON/OFF)
    - Test mode button (systematic comparison)
    - Test results display
    """

    def __init__(
        self,
        density_field: DensityField,
        prop_main: Propeller,
        prop_follower: Propeller,
        synchrophaser: Synchrophaser,
    ):
        """
        Initialize visualizer.

        Args:
            density_field: DensityField instance
            prop_main: Main propeller (reference)
            prop_follower: Follower propeller (controlled by synchro)
            synchrophaser: Synchrophaser controller
        """
        self.density_field = density_field
        self.prop_main = prop_main
        self.prop_follower = prop_follower
        self.synchro = synchrophaser
        self.tester = SynchrophaserTester()

        # Simulation state
        self.sim_time = 0.0
        self.is_paused = False
        self.speed_multiplier = 1.0
        self.last_update_time = time.time()
        self.fps_history = []

        # Store nominal RPM for follower (synchro adjusts this)
        self.follower_base_rpm = prop_follower.rpm_nominal

        # Time-series data storage
        max_points = int(TIMESERIES_WINDOW * TIMESERIES_UPDATE_RATE)
        self.history_time = deque(maxlen=max_points)
        self.history_rpm_main = deque(maxlen=max_points)
        self.history_rpm_follower = deque(maxlen=max_points)
        self.history_density_main = deque(maxlen=max_points)
        self.history_density_follower = deque(maxlen=max_points)
        self.last_history_update = 0.0
        self.history_update_interval = 1.0 / TIMESERIES_UPDATE_RATE

        # Create spatial grid
        self.x_coords = np.linspace(0, DOMAIN_WIDTH, GRID_RESOLUTION_X)
        self.y_coords = np.linspace(
            -DOMAIN_HEIGHT / 2, DOMAIN_HEIGHT / 2, GRID_RESOLUTION_Y
        )

        # Set up the figure and axes
        self._setup_figure()

        # Animation object
        self.animation = None

    def _setup_figure(self):
        """Create figure with all visualization elements."""
        self.fig = plt.figure(figsize=(18, 10))
        self.fig.suptitle(
            'Twin Propeller Synchrophaser - Phase 3',
            fontsize=16,
            fontweight='bold',
        )

        # Layout:
        # [0,0-2] Main density field (3 cols)
        # [1,0-2] Time-series plot (3 cols)
        # [2,0-1] Controls                       [2,2] Info/Results panel

        # Main density field plot
        self.ax_main = plt.subplot2grid((3, 3), (0, 0), colspan=3)
        self.ax_main.set_xlabel('X Position (m)')
        self.ax_main.set_ylabel('Y Position (m)')
        self.ax_main.set_title('Density Field with Twin Propellers (Main=Red, Follower=Blue)')
        self.ax_main.set_xlim(0, DOMAIN_WIDTH)
        self.ax_main.set_ylim(-DOMAIN_HEIGHT / 2, DOMAIN_HEIGHT / 2)

        # Initialize density field plot
        X, Y = np.meshgrid(self.x_coords, self.y_coords)
        initial_grid = self.density_field.get_density_grid(
            self.x_coords, self.y_coords, 0.0
        )

        self.im = self.ax_main.pcolormesh(
            X, Y, initial_grid,
            cmap=COLORMAP,
            shading='auto',
            vmin=self.density_field.rho_min,
            vmax=self.density_field.rho_max,
        )

        # Colorbar
        self.cbar = self.fig.colorbar(self.im, ax=self.ax_main, fraction=0.046)
        self.cbar.set_label('Density (kg/m³)', rotation=270, labelpad=15)

        # Propeller markers
        self.prop_main_circle = Circle(
            (self.prop_main.x, self.prop_main.y),
            PROPELLER_RADIUS * 4,
            color='red', fill=True, alpha=0.8, zorder=10,
            label='Main'
        )
        self.ax_main.add_patch(self.prop_main_circle)

        self.prop_follower_circle = Circle(
            (self.prop_follower.x, self.prop_follower.y),
            PROPELLER_RADIUS * 4,
            color='blue', fill=True, alpha=0.8, zorder=10,
            label='Follower'
        )
        self.ax_main.add_patch(self.prop_follower_circle)

        self.ax_main.legend(loc='upper left')

        # Time-series plot
        self.ax_timeseries = plt.subplot2grid((3, 3), (1, 0), colspan=3)
        self._setup_timeseries()

        # Info/Results panel
        self.ax_info = plt.subplot2grid((3, 3), (2, 2))
        self.ax_info.axis('off')
        self.info_text = self.ax_info.text(
            0.05, 0.95, '', transform=self.ax_info.transAxes,
            verticalalignment='top', fontfamily='monospace', fontsize=7
        )

        # Control widgets
        self._setup_controls()

        plt.tight_layout()

    def _setup_timeseries(self):
        """Create time-series plot for both propellers."""
        self.ax_timeseries.set_xlabel('Time (s)')
        self.ax_timeseries.set_ylabel('RPM')
        self.ax_timeseries.set_title('Propeller RPM (Main=Red, Follower=Blue)')
        self.ax_timeseries.grid(True, alpha=0.3)

        # Initialize RPM lines
        self.line_rpm_main, = self.ax_timeseries.plot(
            [], [], 'r-', linewidth=2, label='Main RPM', alpha=0.8
        )
        self.line_rpm_follower, = self.ax_timeseries.plot(
            [], [], 'b-', linewidth=2, label='Follower RPM', alpha=0.8
        )

        # Nominal RPM reference line
        self.ax_timeseries.axhline(
            PROPELLER_RPM_NOMINAL, color='gray',
            linestyle='--', linewidth=1, label='Nominal', alpha=0.5
        )

        self.ax_timeseries.legend(loc='upper right')

    def _setup_controls(self):
        """Create control sliders and buttons."""
        # Slider area
        slider_height = 0.02
        slider_spacing = 0.04
        slider_left = 0.12
        slider_width = 0.25

        # Wavelength slider
        self.ax_wavelength = plt.axes([slider_left, 0.08, slider_width, slider_height])
        self.slider_wavelength = Slider(
            self.ax_wavelength, 'Wavelength (m)',
            WAVELENGTH_MIN, WAVELENGTH_MAX,
            valinit=WAVELENGTH_DEFAULT, valstep=10.0,
        )
        self.slider_wavelength.on_changed(self._on_wavelength_change)

        # Drift velocity slider
        self.ax_drift = plt.axes([slider_left, 0.08 - slider_spacing, slider_width, slider_height])
        self.slider_drift = Slider(
            self.ax_drift, 'Drift (m/s)',
            DRIFT_VELOCITY_MIN, DRIFT_VELOCITY_MAX,
            valinit=DRIFT_VELOCITY_DEFAULT, valstep=5.0,
        )
        self.slider_drift.on_changed(self._on_drift_change)

        # Octaves slider
        self.ax_octaves = plt.axes([slider_left, 0.08 - 2 * slider_spacing, slider_width, slider_height])
        self.slider_octaves = Slider(
            self.ax_octaves, 'Octaves',
            NUM_OCTAVES_MIN, NUM_OCTAVES_MAX,
            valinit=NUM_OCTAVES_DEFAULT, valstep=1,
        )
        self.slider_octaves.on_changed(self._on_octaves_change)

        # Buttons (right side)
        btn_x_start = 0.45
        btn_width = 0.10
        btn_height = 0.03
        btn_spacing = 0.04

        # Play/Pause button
        self.ax_playpause = plt.axes([btn_x_start, 0.08, btn_width, btn_height])
        self.btn_playpause = Button(self.ax_playpause, 'Pause')
        self.btn_playpause.on_clicked(self._on_playpause)

        # Synchrophaser toggle
        self.ax_synchro_toggle = plt.axes([btn_x_start, 0.08 - btn_spacing, btn_width, btn_height])
        self.btn_synchro_toggle = Button(
            self.ax_synchro_toggle,
            'Synchro: OFF',
            color='lightcoral'
        )
        self.btn_synchro_toggle.on_clicked(self._on_synchro_toggle)

        # Test button
        self.ax_test = plt.axes([btn_x_start, 0.08 - 2 * btn_spacing, btn_width, btn_height])
        self.btn_test = Button(self.ax_test, 'Run Test', color='lightblue')
        self.btn_test.on_clicked(self._on_test)

        # Copy results button
        self.ax_copy = plt.axes([btn_x_start + 0.11, 0.08 - 2 * btn_spacing, btn_width, btn_height])
        self.btn_copy = Button(self.ax_copy, 'Copy Results', color='lightyellow')
        self.btn_copy.on_clicked(self._on_copy)

        # Speed buttons
        self.speed_buttons = []
        speeds = [0.5, 1.0, 2.0, 4.0]
        for i, speed in enumerate(speeds):
            ax_speed = plt.axes([btn_x_start + i * 0.06, 0.02, 0.05, 0.025])
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

    def _on_synchro_toggle(self, event):
        """Toggle synchrophaser on/off."""
        if self.synchro.enabled:
            self.synchro.disable()
            self.btn_synchro_toggle.label.set_text('Synchro: OFF')
            self.btn_synchro_toggle.color = 'lightcoral'
            self.btn_synchro_toggle.hovercolor = 'salmon'
        else:
            self.synchro.enable()
            self.synchro.reset_stats()
            self.btn_synchro_toggle.label.set_text('Synchro: ON')
            self.btn_synchro_toggle.color = 'lightgreen'
            self.btn_synchro_toggle.hovercolor = 'lime'

    def _on_test(self, event):
        """Start systematic test."""
        if not self.tester.is_testing:
            self.tester.start_test(self.sim_time)
            self.synchro.disable()
            print("\n" + "="*60)
            print("STARTING SYSTEMATIC TEST")
            print("="*60)
            print("Phase 1: Synchrophaser OFF (60s)")
            print("Phase 2: Synchrophaser ON (60s)")
            print("="*60)

    def _on_copy(self, event):
        """Copy test results to clipboard."""
        if self.tester.results:
            import pyperclip
            clipboard_text = self.tester.get_results_clipboard()
            try:
                pyperclip.copy(clipboard_text)
                print("\n✓ Test results copied to clipboard!")
            except:
                # Fallback: just print to console
                print("\n" + "="*60)
                print("CLIPBOARD TEXT (copy manually):")
                print("="*60)
                print(clipboard_text)
                print("="*60)
        else:
            print("\n⚠️  No test results available. Run a test first!")

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

            # Update propellers
            self.prop_main.update(sim_dt, self.sim_time, self.density_field)
            self.prop_follower.update(sim_dt, self.sim_time, self.density_field)

            # Update synchrophaser with TRUE PHASE from blade positions
            rpm_correction = self.synchro.update(
                self.prop_main.blade_angle,
                self.prop_follower.blade_angle,
                sim_dt
            )

            # Apply synchrophaser correction to follower's target RPM
            if self.synchro.enabled:
                # Set target to base + correction (absolute, not incremental)
                new_target = self.follower_base_rpm + rpm_correction
                # Clamp to reasonable range to prevent runaway
                new_target = np.clip(new_target, 2350, 2450)
                self.prop_follower.set_rpm_target(new_target)
            else:
                # When disabled, reset to base RPM
                self.prop_follower.set_rpm_target(self.follower_base_rpm)

            # Handle test mode
            if self.tester.is_testing:
                should_enable, status = self.tester.update(
                    self.sim_time,
                    self.prop_main.rpm,
                    self.prop_follower.rpm,
                    self.synchro.phase_error,
                    TEST_MODE_DURATION
                )
                if should_enable and not self.synchro.enabled:
                    self.synchro.enable()
                    self.synchro.reset_stats()
                    print("\n>>> Switching to Synchrophaser ON <<<\n")

                if not self.tester.is_testing and self.tester.results:
                    print(self.tester.get_results_string())
                    print("\n" + "="*60)
                    print("📋 COPY-PASTE RESULTS (for sharing):")
                    print("="*60)
                    print(self.tester.get_results_clipboard())
                    print("="*60)
                    print("Or click 'Copy Results' button to copy to clipboard")

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

        # Update time-series history
        if self.sim_time - self.last_history_update >= self.history_update_interval:
            self.history_time.append(self.sim_time)
            self.history_rpm_main.append(self.prop_main.rpm)
            self.history_rpm_follower.append(self.prop_follower.rpm)
            self.history_density_main.append(self.prop_main.rho_local)
            self.history_density_follower.append(self.prop_follower.rho_local)
            self.last_history_update = self.sim_time

        # Update time-series plot
        self._update_timeseries()

        # Update info panel
        self._update_info_panel(avg_fps)

        return [self.im, self.line_rpm_main, self.line_rpm_follower]

    def _update_timeseries(self):
        """Update time-series plot with new data."""
        if len(self.history_time) > 0:
            times = list(self.history_time)
            rpms_main = list(self.history_rpm_main)
            rpms_follower = list(self.history_rpm_follower)

            # Update lines
            self.line_rpm_main.set_data(times, rpms_main)
            self.line_rpm_follower.set_data(times, rpms_follower)

            # Update x-axis limits (rolling window)
            if times[-1] > TIMESERIES_WINDOW:
                self.ax_timeseries.set_xlim(
                    times[-1] - TIMESERIES_WINDOW, times[-1]
                )
            else:
                self.ax_timeseries.set_xlim(0, max(TIMESERIES_WINDOW, times[-1]))

            # Update y-axis limits
            all_rpms = rpms_main + rpms_follower
            if len(all_rpms) > 1:
                r_min, r_max = min(all_rpms), max(all_rpms)
                r_margin = max(20, (r_max - r_min) * 0.1)
                self.ax_timeseries.set_ylim(
                    max(RPM_MIN_DISPLAY, r_min - r_margin),
                    min(RPM_MAX_DISPLAY, r_max + r_margin)
                )

    def _update_info_panel(self, avg_fps):
        """Update info text panel."""
        synchro_stats = self.synchro.get_stats()
        rpm_diff = abs(self.prop_main.rpm - self.prop_follower.rpm)

        # Check if in test mode
        test_status = ""
        if self.tester.is_testing:
            test_status = f"\n{'='*25}\nTEST MODE ACTIVE\n"
            if self.tester.test_phase == 'off':
                elapsed = self.sim_time - self.tester.phase_start_time
                test_status += f"Synchro OFF: {elapsed:.0f}/{TEST_MODE_DURATION:.0f}s\n"
            elif self.tester.test_phase == 'on':
                elapsed = self.sim_time - self.tester.phase_start_time
                test_status += f"Synchro ON:  {elapsed:.0f}/{TEST_MODE_DURATION:.0f}s\n"
            test_status += f"{'='*25}\n"
        elif self.tester.results:
            # Show test results
            r = self.tester.results
            test_status = f"\n{'='*25}\nTEST RESULTS\n{'='*25}\n"
            test_status += f"RPM Error:\n"
            test_status += f"  OFF: {r['off_mean_rpm_error']:.2f}\n"
            test_status += f"  ON:  {r['on_mean_rpm_error']:.2f}\n"
            test_status += f"  Improve: {r['rpm_error_improvement_pct']:.1f}%\n"
            test_status += f"{'='*25}\n"

        info_str = (
            f"Time: {self.sim_time:.1f}s\n"
            f"FPS: {avg_fps:.0f}\n"
            f"Speed: {self.speed_multiplier}×\n"
            f"{'PAUSED' if self.is_paused else 'RUNNING'}\n\n"
            f"--- Propellers ---\n"
            f"Main:     {self.prop_main.rpm:.1f} RPM\n"
            f"Follower: {self.prop_follower.rpm:.1f} RPM\n"
            f"Diff:     {rpm_diff:.1f} RPM\n\n"
            f"--- Synchrophaser ---\n"
            f"Status: {'ON' if synchro_stats['enabled'] else 'OFF'}\n"
            f"Phase Err: {synchro_stats['phase_error_deg']:.2f}°\n"
            f"RPM Corr: {synchro_stats['rpm_correction']:.1f}\n"
            f"P-term: {synchro_stats['proportional_term']:.2f}\n"
            f"I-term: {synchro_stats['integral_term']:.2f}\n"
            f"{test_status}"
        )
        self.info_text.set_text(info_str)

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
