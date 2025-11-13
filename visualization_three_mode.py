"""
Three-mode twin propeller visualization with synchrophaser comparison.

Modes:
1. OFF - No synchronization (baseline for comparison)
2. BASELINE - Proven PID synchrophaser (62% improvement)
3. ADVANCED - Phase-Frequency Detector (64% improvement)

Interactive controls allow switching between modes in real-time to see
the difference in performance.

Author: Phase 3 complete implementation
Date: 2025-11-12
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from collections import deque

from density_field import DensityField
from propeller import Propeller
from synchrophaser import Synchrophaser
from pfd_synchrophaser import PFDSynchrophaser
from propeller_sound import PropellerSoundGenerator
from parameters import (
    DOMAIN_WIDTH,
    DOMAIN_HEIGHT,
    GRID_RESOLUTION_X,
    GRID_RESOLUTION_Y,
    TARGET_FPS,
    COLORMAP,
    PROPELLER_X_DEFAULT,
    PROPELLER_LEFT_Y,
    PROPELLER_RIGHT_Y,
    PROPELLER_RPM_NOMINAL,
    TIMESERIES_WINDOW,
)


class ThreeModeSynchrophaserVisualizer:
    """
    Interactive visualization comparing three synchrophaser modes.

    Features:
    - Three-mode toggle: OFF / BASELINE / ADVANCED (PFD)
    - Real-time mode switching
    - Time-series showing both RPM traces
    - Info panel with current mode and statistics
    - Color-coded mode indicator
    - Propeller sound with beating effect when out of sync
    """

    def __init__(
        self,
        density_field: DensityField,
        prop_main: Propeller,
        prop_follower: Propeller,
        synchro_baseline: Synchrophaser,
        synchro_advanced: PFDSynchrophaser,
    ):
        """
        Initialize three-mode visualizer.

        Args:
            density_field: Atmospheric density field
            prop_main: Main propeller (reference)
            prop_follower: Follower propeller (controlled)
            synchro_baseline: Proven PID synchrophaser
            synchro_advanced: Advanced PFD synchrophaser
        """
        self.density_field = density_field
        self.prop_main = prop_main
        self.prop_follower = prop_follower
        self.synchro_baseline = synchro_baseline
        self.synchro_advanced = synchro_advanced

        # Current mode: 'off', 'baseline', or 'advanced'
        self.mode = 'off'

        # Base RPM for follower (when synchro disabled or adjusting)
        self.follower_base_rpm = PROPELLER_RPM_NOMINAL

        # Sound system
        self.sound = PropellerSoundGenerator(num_blades=3, volume=0.15)
        self.sound_enabled = False

        # Time tracking
        self.sim_time = 0.0
        self.last_update_time = None
        self.is_paused = False
        self.speed_multiplier = 1.0

        # History for time-series plots
        self.time_history = deque(maxlen=int(TIMESERIES_WINDOW * 10))
        self.rpm_main_history = deque(maxlen=int(TIMESERIES_WINDOW * 10))
        self.rpm_follower_history = deque(maxlen=int(TIMESERIES_WINDOW * 10))
        self.density_main_history = deque(maxlen=int(TIMESERIES_WINDOW * 10))
        self.density_follower_history = deque(maxlen=int(TIMESERIES_WINDOW * 10))

        # Rolling error tracking (15 second window)
        self.error_history = deque()  # Stores (timestamp, error) tuples
        self.rolling_window_seconds = 15.0
        self.rolling_avg_error = 0.0

        # Coordinates for density field visualization
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
            'Three-Mode Synchrophaser Comparison',
            fontsize=16,
            fontweight='bold',
        )

        # Layout:
        # [0,0-2] Main density field (3 cols)
        # [1,0-2] Time-series plot (3 cols)
        # [2,0-1] Mode controls    [2,2] Info panel

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
        self.marker_main = self.ax_main.plot(
            [self.prop_main.x], [self.prop_main.y],
            'ro', markersize=12, label='Main (Red)', zorder=10
        )[0]
        self.marker_follower = self.ax_main.plot(
            [self.prop_follower.x], [self.prop_follower.y],
            'bo', markersize=12, label='Follower (Blue)', zorder=10
        )[0]
        self.ax_main.legend(loc='upper left')

        # Time-series plot
        self.ax_timeseries = plt.subplot2grid((3, 3), (1, 0), colspan=3)
        self.ax_timeseries.set_xlabel('Time (s)')
        self.ax_timeseries.set_ylabel('RPM')
        self.ax_timeseries.set_title('Propeller RPM Over Time')
        self.ax_timeseries.grid(True, alpha=0.3)

        # RPM history lines
        self.line_rpm_main, = self.ax_timeseries.plot(
            [], [], 'r-', linewidth=2, label='Main RPM'
        )
        self.line_rpm_follower, = self.ax_timeseries.plot(
            [], [], 'b-', linewidth=2, label='Follower RPM'
        )
        self.line_rpm_nominal, = self.ax_timeseries.plot(
            [], [], 'k--', linewidth=1, alpha=0.5, label='Nominal (2400)'
        )
        self.ax_timeseries.legend(loc='upper right')
        self.ax_timeseries.set_ylim(2350, 2450)

        # Mode control panel
        self.ax_controls = plt.subplot2grid((3, 3), (2, 0), colspan=2)
        self.ax_controls.axis('off')

        # Mode selection buttons (in bottom control area)
        button_width = 0.12
        button_height = 0.08
        button_y = 0.15  # Bottom area

        # Left side: Mode buttons
        self.ax_btn_off = plt.axes([0.05, button_y, button_width, button_height])
        self.btn_off = Button(self.ax_btn_off, 'OFF\n(No Sync)', color='lightcoral')
        self.btn_off.on_clicked(lambda event: self.set_mode('off'))

        self.ax_btn_baseline = plt.axes([0.19, button_y, button_width, button_height])
        self.btn_baseline = Button(self.ax_btn_baseline, 'BASELINE\n(Proven PID)', color='lightgray')
        self.btn_baseline.on_clicked(lambda event: self.set_mode('baseline'))

        self.ax_btn_advanced = plt.axes([0.33, button_y, button_width, button_height])
        self.btn_advanced = Button(self.ax_btn_advanced, 'ADVANCED\n(PFD)', color='lightgray')
        self.btn_advanced.on_clicked(lambda event: self.set_mode('advanced'))

        # Right side: Control buttons
        self.ax_btn_pause = plt.axes([0.48, button_y, 0.08, button_height])
        self.btn_pause = Button(self.ax_btn_pause, 'Pause', color='lightyellow')
        self.btn_pause.on_clicked(self.toggle_pause)

        # Speed buttons
        self.ax_btn_speed_down = plt.axes([0.58, button_y, 0.06, button_height])
        self.btn_speed_down = Button(self.ax_btn_speed_down, '0.5x', color='lightblue')
        self.btn_speed_down.on_clicked(lambda event: self.set_speed(0.5))

        self.ax_btn_speed_normal = plt.axes([0.65, button_y, 0.06, button_height])
        self.btn_speed_normal = Button(self.ax_btn_speed_normal, '1x', color='lightgreen')
        self.btn_speed_normal.on_clicked(lambda event: self.set_speed(1.0))

        self.ax_btn_speed_up = plt.axes([0.72, button_y, 0.06, button_height])
        self.btn_speed_up = Button(self.ax_btn_speed_up, '2x', color='lightblue')
        self.btn_speed_up.on_clicked(lambda event: self.set_speed(2.0))

        # Sound toggle button
        self.ax_btn_sound = plt.axes([0.80, button_y, 0.08, button_height])
        self.btn_sound = Button(self.ax_btn_sound, 'Sound\nOFF', color='lightgray')
        self.btn_sound.on_clicked(self.toggle_sound)

        # Info panel
        self.ax_info = plt.subplot2grid((3, 3), (2, 2))
        self.ax_info.axis('off')
        self.info_text = self.ax_info.text(
            0.05, 0.95, '', transform=self.ax_info.transAxes,
            verticalalignment='top', fontfamily='monospace', fontsize=9
        )

        # Update initial button colors
        self._update_button_colors()

        plt.tight_layout()

    def set_mode(self, mode: str):
        """
        Set synchrophaser mode.

        Args:
            mode: 'off', 'baseline', or 'advanced'
        """
        if mode not in ['off', 'baseline', 'advanced']:
            return

        # Disable all synchrophasers first
        self.synchro_baseline.disable()
        self.synchro_advanced.disable()

        # Set new mode
        self.mode = mode

        # Enable appropriate synchrophaser
        if mode == 'baseline':
            self.synchro_baseline.enable()
        elif mode == 'advanced':
            self.synchro_advanced.enable()

        # Reset follower to base RPM
        self.prop_follower.set_rpm_target(self.follower_base_rpm)

        # Update button colors
        self._update_button_colors()

        print(f"\nMode changed to: {mode.upper()}")

    def _update_button_colors(self):
        """Update button colors based on active mode."""
        # Reset all to gray
        self.btn_off.color = 'lightgray'
        self.btn_baseline.color = 'lightgray'
        self.btn_advanced.color = 'lightgray'

        # Highlight active mode
        if self.mode == 'off':
            self.btn_off.color = 'lightcoral'
        elif self.mode == 'baseline':
            self.btn_baseline.color = 'lightgreen'
        elif self.mode == 'advanced':
            self.btn_advanced.color = 'lightblue'

        # Force redraw
        self.fig.canvas.draw_idle()

    def toggle_pause(self, event):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        self.btn_pause.label.set_text('Resume' if self.is_paused else 'Pause')

    def set_speed(self, speed: float):
        """Set simulation speed multiplier."""
        self.speed_multiplier = speed

    def toggle_sound(self, event):
        """Toggle propeller sound on/off."""
        if self.sound_enabled:
            # Turn sound off
            self.sound.stop()
            self.sound_enabled = False
            self.btn_sound.label.set_text('Sound\nOFF')
            self.btn_sound.color = 'lightgray'
            print("Sound disabled")
        else:
            # Turn sound on
            if not self.sound.is_available():
                print("Sound not available (install sounddevice: pip install sounddevice)")
                return

            if self.sound.start():
                self.sound_enabled = True
                self.btn_sound.label.set_text('Sound\nON')
                self.btn_sound.color = 'lightgreen'
                print("Sound enabled - Listen for beating effect when out of sync!")
            else:
                print("Failed to start sound")

    def update_frame(self, frame):
        """Update animation frame."""
        import time

        # Compute real-time delta
        current_time = time.time()
        if self.last_update_time is None:
            real_dt = 1.0 / TARGET_FPS
        else:
            real_dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Update simulation
        if not self.is_paused:
            sim_dt = real_dt * self.speed_multiplier
            self.sim_time += sim_dt

            # Update propellers
            self.prop_main.update(sim_dt, self.sim_time, self.density_field)
            self.prop_follower.update(sim_dt, self.sim_time, self.density_field)

            # Update synchrophaser based on mode
            rpm_correction = 0.0

            if self.mode == 'baseline':
                # Baseline: Regular phase-based PID
                rpm_correction = self.synchro_baseline.update(
                    self.prop_main.blade_angle,
                    self.prop_follower.blade_angle,
                    sim_dt
                )
            elif self.mode == 'advanced':
                # Advanced: Phase-Frequency Detector
                rpm_correction = self.synchro_advanced.update(
                    self.prop_main.blade_angle,
                    self.prop_follower.blade_angle,
                    self.prop_main.omega,
                    self.prop_follower.omega,
                    sim_dt
                )

            # Apply synchrophaser correction to follower's target RPM
            if self.mode != 'off':
                new_target = self.follower_base_rpm + rpm_correction
                new_target = np.clip(new_target, 2350, 2450)
                self.prop_follower.set_rpm_target(new_target)
            else:
                # When OFF, reset to base RPM
                self.prop_follower.set_rpm_target(self.follower_base_rpm)

            # Update history
            self.time_history.append(self.sim_time)
            self.rpm_main_history.append(self.prop_main.rpm)
            self.rpm_follower_history.append(self.prop_follower.rpm)
            self.density_main_history.append(self.prop_main.rho_local)
            self.density_follower_history.append(self.prop_follower.rho_local)

            # Update rolling error history
            rpm_error = abs(self.prop_main.rpm - self.prop_follower.rpm)
            self.error_history.append((self.sim_time, rpm_error))

            # Remove old errors outside the rolling window
            cutoff_time = self.sim_time - self.rolling_window_seconds
            while self.error_history and self.error_history[0][0] < cutoff_time:
                self.error_history.popleft()

            # Compute rolling average
            if self.error_history:
                self.rolling_avg_error = np.mean([err for _, err in self.error_history])
            else:
                self.rolling_avg_error = 0.0

            # Update sound with current RPMs
            if self.sound_enabled:
                self.sound.update_rpms(self.prop_main.rpm, self.prop_follower.rpm)

        # Update density field visualization
        density_grid = self.density_field.get_density_grid(
            self.x_coords, self.y_coords, self.sim_time
        )
        self.im.set_array(density_grid.ravel())

        # Update time-series plot
        if len(self.time_history) > 0:
            times = np.array(self.time_history)
            rpm_main = np.array(self.rpm_main_history)
            rpm_follower = np.array(self.rpm_follower_history)

            self.line_rpm_main.set_data(times, rpm_main)
            self.line_rpm_follower.set_data(times, rpm_follower)
            self.line_rpm_nominal.set_data(
                [times[0], times[-1]],
                [PROPELLER_RPM_NOMINAL, PROPELLER_RPM_NOMINAL]
            )

            # Auto-scale x-axis to show recent window
            self.ax_timeseries.set_xlim(
                max(0, self.sim_time - TIMESERIES_WINDOW),
                self.sim_time
            )

        # Update info panel
        self._update_info_panel()

        return [self.im, self.marker_main, self.marker_follower,
                self.line_rpm_main, self.line_rpm_follower, self.line_rpm_nominal]

    def _update_info_panel(self):
        """Update info panel with current statistics."""
        # Mode display
        mode_display = {
            'off': 'OFF (No Sync)',
            'baseline': 'BASELINE (PID)',
            'advanced': 'ADVANCED (PFD)'
        }

        # Get active synchrophaser stats
        if self.mode == 'baseline':
            stats = self.synchro_baseline.get_stats()
        elif self.mode == 'advanced':
            stats = self.synchro_advanced.get_stats()
        else:
            stats = None

        # Compute current errors
        rpm_error = abs(self.prop_main.rpm - self.prop_follower.rpm)

        if stats:
            phase_error_deg = stats['phase_error_deg']
            rpm_correction = stats['rpm_correction']
        else:
            phase_error_deg = 0.0
            rpm_correction = 0.0

        # Format info text
        info_lines = [
            f"Mode: {mode_display[self.mode]}",
            f"Time: {self.sim_time:.1f}s",
            f"Speed: {self.speed_multiplier}x",
            "",
            "Propeller RPM:",
            f"  Main:     {self.prop_main.rpm:7.1f}",
            f"  Follower: {self.prop_follower.rpm:7.1f}",
            f"  Error:    {rpm_error:7.2f}",
            f"  15s Avg:  {self.rolling_avg_error:7.2f}",
            "",
            "Density (kg/m³):",
            f"  Main:     {self.prop_main.rho_local:.4f}",
            f"  Follower: {self.prop_follower.rho_local:.4f}",
        ]

        if self.mode != 'off':
            info_lines.extend([
                "",
                "Synchrophaser:",
                f"  Phase Err: {phase_error_deg:6.2f}°",
                f"  Correction: {rpm_correction:+6.2f} RPM",
            ])

            if self.mode == 'advanced' and hasattr(self.synchro_advanced, 'freq_error_rpm'):
                info_lines.append(f"  Freq Err:  {self.synchro_advanced.freq_error_rpm:6.2f} RPM")

        self.info_text.set_text('\n'.join(info_lines))

    def start(self):
        """Start the animation."""
        self.animation = FuncAnimation(
            self.fig,
            self.update_frame,
            interval=1000 / TARGET_FPS,
            blit=False,
            cache_frame_data=False,
        )
        plt.show()

    def __del__(self):
        """Cleanup when visualizer is destroyed."""
        if hasattr(self, 'sound') and self.sound_enabled:
            self.sound.stop()


def main():
    """Create and run three-mode synchrophaser visualization."""
    print("="*60)
    print("THREE-MODE SYNCHROPHASER VISUALIZATION")
    print("="*60)

    # Create density field
    field = DensityField()

    # Create twin propellers (vertically separated)
    prop_main = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_LEFT_Y)
    prop_follower = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_RIGHT_Y)

    print(f"\nPropeller positions:")
    print(f"  Main (Red):     ({prop_main.x:.0f}m, {prop_main.y:.0f}m)")
    print(f"  Follower (Blue): ({prop_follower.x:.0f}m, {prop_follower.y:.0f}m)")
    print(f"  Vertical separation: {abs(prop_main.y - prop_follower.y):.0f}m")

    # Create synchrophasers
    synchro_baseline = Synchrophaser()
    synchro_advanced = PFDSynchrophaser()

    print(f"\nModes available:")
    print(f"  OFF:      No synchronization")
    print(f"  BASELINE: Proven PID (62% improvement)")
    print(f"  ADVANCED: Phase-Frequency Detector (64% improvement)")

    print(f"\nStarting visualization...")
    print(f"  - Click buttons to switch modes")
    print(f"  - Compare RPM traces (red vs blue)")
    print(f"  - Watch info panel for statistics")

    # Create and start visualizer
    viz = ThreeModeSynchrophaserVisualizer(
        field, prop_main, prop_follower,
        synchro_baseline, synchro_advanced
    )
    viz.start()


if __name__ == '__main__':
    main()
