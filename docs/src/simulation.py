"""
Synchrophaser simulation for web browser using PyScript.

This runs the full physics simulation in the browser and renders to Canvas.
"""

import asyncio
import numpy as np
from js import (
    document, window, requestAnimationFrame,
    console, onSimulationReady, Math
)
from pyodide.ffi import create_proxy
from collections import deque

# Import our simulation modules
from density_field import DensityField
from propeller import Propeller
from synchrophaser import Synchrophaser
from pfd_synchrophaser import PFDSynchrophaser
from parameters import (
    PROPELLER_X_DEFAULT,
    PROPELLER_LEFT_Y,
    PROPELLER_RIGHT_Y,
    PROPELLER_RPM_NOMINAL,
    DOMAIN_WIDTH,
    DOMAIN_HEIGHT,
    GRID_RESOLUTION_X,
    GRID_RESOLUTION_Y,
)


class WebSimulation:
    """Main simulation class for web browser."""

    def __init__(self):
        """Initialize simulation."""
        console.log("Initializing simulation...")

        # Create density field
        self.density_field = DensityField()

        # Create twin propellers
        self.prop_main = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_LEFT_Y)
        self.prop_follower = Propeller(x=PROPELLER_X_DEFAULT, y=PROPELLER_RIGHT_Y)

        # Create synchrophasers
        self.synchro_baseline = Synchrophaser()
        self.synchro_advanced = PFDSynchrophaser()

        # Simulation state
        self.mode = 'off'
        self.sim_time = 0.0
        self.last_update_time = None
        self.is_paused = False
        self.follower_base_rpm = PROPELLER_RPM_NOMINAL

        # Rolling error tracking (15 second window)
        self.error_history = deque()
        self.rolling_window_seconds = 15.0
        self.rolling_avg_error = 0.0

        # Canvas setup
        self.canvas = document.getElementById('mainCanvas')
        self.ctx = self.canvas.getContext('2d')

        # Set canvas size
        self.canvas.width = 800
        self.canvas.height = 500

        # Grid for visualization
        self.grid_x = np.linspace(0, DOMAIN_WIDTH, 40)  # Reduced resolution for performance
        self.grid_y = np.linspace(-DOMAIN_HEIGHT / 2, DOMAIN_HEIGHT / 2, 25)

        console.log("Simulation initialized")

    def set_mode(self, mode):
        """Set synchrophaser mode."""
        console.log(f"Setting mode to: {mode}")

        # Disable all synchrophasers
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

    def set_paused(self, paused):
        """Set pause state."""
        self.is_paused = paused
        console.log(f"Paused: {paused}")

    def update_physics(self, dt):
        """Update physics simulation."""
        if self.is_paused:
            return

        self.sim_time += dt

        # Update propellers
        self.prop_main.update(dt, self.sim_time, self.density_field)
        self.prop_follower.update(dt, self.sim_time, self.density_field)

        # Update synchrophaser based on mode
        rpm_correction = 0.0

        if self.mode == 'baseline':
            rpm_correction = self.synchro_baseline.update(
                self.prop_main.blade_angle,
                self.prop_follower.blade_angle,
                dt
            )
        elif self.mode == 'advanced':
            rpm_correction = self.synchro_advanced.update(
                self.prop_main.blade_angle,
                self.prop_follower.blade_angle,
                self.prop_main.omega,
                self.prop_follower.omega,
                dt
            )

        # Apply correction
        if self.mode != 'off':
            new_target = self.follower_base_rpm + rpm_correction
            new_target = np.clip(new_target, 2350, 2450)
            self.prop_follower.set_rpm_target(new_target)
        else:
            self.prop_follower.set_rpm_target(self.follower_base_rpm)

        # Update rolling error history
        rpm_error = abs(self.prop_main.rpm - self.prop_follower.rpm)
        self.error_history.append((self.sim_time, rpm_error))

        # Remove old errors
        cutoff_time = self.sim_time - self.rolling_window_seconds
        while self.error_history and self.error_history[0][0] < cutoff_time:
            self.error_history.popleft()

        # Compute rolling average
        if self.error_history:
            self.rolling_avg_error = np.mean([err for _, err in self.error_history])
        else:
            self.rolling_avg_error = 0.0

    def render(self):
        """Render visualization to canvas."""
        # Clear canvas
        self.ctx.fillStyle = '#ffffff'
        self.ctx.fillRect(0, 0, self.canvas.width, self.canvas.height)

        # Get density grid
        density_grid = self.density_field.get_density_grid(
            self.grid_x, self.grid_y, self.sim_time
        )

        # Draw density field
        cell_width = self.canvas.width / len(self.grid_x)
        cell_height = self.canvas.height / len(self.grid_y)

        for i in range(len(self.grid_y)):
            for j in range(len(self.grid_x)):
                # Map density to color (blue to red)
                rho = density_grid[i, j]
                rho_norm = (rho - self.density_field.rho_min) / (
                    self.density_field.rho_max - self.density_field.rho_min
                )
                rho_norm = np.clip(rho_norm, 0, 1)

                # Color interpolation (blue → cyan → yellow → red)
                if rho_norm < 0.5:
                    # Blue to cyan
                    t = rho_norm * 2
                    r = int(0 * (1-t) + 0 * t)
                    g = int(0 * (1-t) + 255 * t)
                    b = int(255 * (1-t) + 255 * t)
                else:
                    # Cyan to red
                    t = (rho_norm - 0.5) * 2
                    r = int(0 * (1-t) + 255 * t)
                    g = int(255 * (1-t) + 0 * t)
                    b = int(255 * (1-t) + 0 * t)

                self.ctx.fillStyle = f'rgb({r},{g},{b})'
                self.ctx.fillRect(
                    j * cell_width,
                    i * cell_height,
                    cell_width,
                    cell_height
                )

        # Draw propellers
        # Convert world coordinates to canvas coordinates
        def world_to_canvas_x(x):
            return (x / DOMAIN_WIDTH) * self.canvas.width

        def world_to_canvas_y(y):
            # y goes from -DOMAIN_HEIGHT/2 to +DOMAIN_HEIGHT/2
            # Canvas y=0 is top, y=height is bottom
            return ((y + DOMAIN_HEIGHT/2) / DOMAIN_HEIGHT) * self.canvas.height

        # Main propeller (red)
        x_main = world_to_canvas_x(self.prop_main.x)
        y_main = world_to_canvas_y(self.prop_main.y)

        self.ctx.fillStyle = '#ef4444'
        self.ctx.beginPath()
        self.ctx.arc(x_main, y_main, 8, 0, 2 * Math.PI)
        self.ctx.fill()
        self.ctx.strokeStyle = '#ffffff'
        self.ctx.lineWidth = 2
        self.ctx.stroke()

        # Follower propeller (blue)
        x_follower = world_to_canvas_x(self.prop_follower.x)
        y_follower = world_to_canvas_y(self.prop_follower.y)

        self.ctx.fillStyle = '#3b82f6'
        self.ctx.beginPath()
        self.ctx.arc(x_follower, y_follower, 8, 0, 2 * Math.PI)
        self.ctx.fill()
        self.ctx.strokeStyle = '#ffffff'
        self.ctx.lineWidth = 2
        self.ctx.stroke()

        # Labels
        self.ctx.fillStyle = '#000000'
        self.ctx.font = '12px Arial'
        self.ctx.fillText('Main', x_main + 12, y_main + 5)
        self.ctx.fillText('Follower', x_follower + 12, y_follower + 5)

    def update_ui(self):
        """Update UI elements with current values."""
        # Time
        document.getElementById('simTime').textContent = f"{self.sim_time:.1f}s"

        # RPMs
        document.getElementById('rpmMain').textContent = f"{self.prop_main.rpm:.1f}"
        document.getElementById('rpmFollower').textContent = f"{self.prop_follower.rpm:.1f}"

        # Error
        rpm_error = abs(self.prop_main.rpm - self.prop_follower.rpm)
        document.getElementById('rpmError').textContent = f"{rpm_error:.2f}"
        document.getElementById('rollingAvg').textContent = f"{self.rolling_avg_error:.2f}"

        # Densities
        document.getElementById('densityMain').textContent = f"{self.prop_main.rho_local:.4f}"
        document.getElementById('densityFollower').textContent = f"{self.prop_follower.rho_local:.4f}"

        # Synchrophaser info (if active)
        if self.mode == 'baseline':
            stats = self.synchro_baseline.get_stats()
            document.getElementById('phaseError').textContent = f"{stats['phase_error_deg']:.2f}°"
            document.getElementById('correction').textContent = f"{stats['rpm_correction']:+.2f}"
        elif self.mode == 'advanced':
            stats = self.synchro_advanced.get_stats()
            document.getElementById('phaseError').textContent = f"{stats['phase_error_deg']:.2f}°"
            document.getElementById('correction').textContent = f"{stats['rpm_correction']:+.2f}"

    async def animate(self):
        """Main animation loop."""
        dt = 0.033  # ~30 FPS

        while True:
            self.update_physics(dt)
            self.render()
            self.update_ui()

            # Yield control back to browser
            await asyncio.sleep(dt)


# Create global simulation instance
sim = WebSimulation()

# Expose to JavaScript
window.sim = sim

# Notify UI that simulation is ready
onSimulationReady()

# Start animation
console.log("Starting animation loop...")
asyncio.ensure_future(sim.animate())
