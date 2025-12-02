"""
Synchrophaser PLL Simulation for PyScript/Browser
==================================================

Lightweight PLL simulation that runs in the browser using PyScript.
Renders to HTML5 Canvas for real-time visualization.
"""

import numpy as np
from js import document, window, setInterval, clearInterval
from pyodide.ffi import create_proxy

# =============================================================================
# PLL COMPONENT PARAMETERS (matching schematic)
# =============================================================================

class PLLParameters:
    """Component values from the 42-component schematic"""
    # Power Supply
    V_SUPPLY = 5.0  # 7805 output

    # Signal Conditioning
    R_PULLUP = 10e3  # 10kΩ
    C_FILTER = 100e-9  # 100nF -> fc = 159Hz

    # Charge Pump
    R_SET = 5000  # 5kΩ -> I_cp = 1mA
    I_CP = V_SUPPLY / R_SET

    # Loop Filter
    RZ = 680  # 680Ω damping
    CINT = 100e-6  # 100µF integrator
    C_HF = 100e-9  # 100nF HF bypass
    ESR = 1.0  # ~1Ω parasitic

    # VCO
    K_VCO = 15.15  # Hz/V at blade freq
    F_CENTER = 45.0  # 45Hz = 900 RPM with 3 blades

    # Motor
    TAU_MOTOR = 0.022  # 22ms time constant
    NUM_BLADES = 3

    # Lock Detector
    LOCK_THRESHOLD = 2.0  # degrees


# =============================================================================
# PLL SIMULATION ENGINE
# =============================================================================

class SynchrophaserSimulation:
    """Type-II Charge Pump PLL Simulation"""

    def __init__(self):
        self.params = PLLParameters()
        self.dt = 0.002  # 2ms timestep
        self.reset()

    def reset(self):
        """Reset to initial conditions"""
        # Get values from sliders
        try:
            self.ref_rpm = float(document.getElementById("main-rpm").value)
            self.fb_rpm = float(document.getElementById("follower-rpm").value)
            self.phase_offset = float(document.getElementById("phase-offset").value)
            self.params.K_VCO = float(document.getElementById("kvco").value)
            self.params.I_CP = float(document.getElementById("icp").value) / 1000
        except:
            self.ref_rpm = 900.0
            self.fb_rpm = 885.0
            self.phase_offset = 45.0

        # Convert to frequencies
        self.f_ref = self.ref_rpm / 60 * self.params.NUM_BLADES
        self.f_fb = self.fb_rpm / 60 * self.params.NUM_BLADES

        # State variables
        self.phase_ref = 0.0
        self.phase_fb = np.deg2rad(self.phase_offset)
        self.v_ctrl = self.params.V_SUPPLY / 2
        self.v_int = 0.0
        self.f_vco = self.f_fb
        self.rpm_follower = self.fb_rpm
        self.is_locked = False

        # History for plotting
        self.history_len = 200
        self.time_history = []
        self.phase_err_history = []
        self.rpm_ref_history = []
        self.rpm_fb_history = []
        self.v_ctrl_history = []

        self.t = 0.0
        self.running = False

    def step(self):
        """Advance simulation by one timestep"""
        # Phase accumulation
        self.phase_ref += 2 * np.pi * self.f_ref * self.dt
        self.phase_fb += 2 * np.pi * self.f_vco * self.dt

        # PFD: Phase error
        phase_err = (self.phase_ref - self.phase_fb) % (2 * np.pi)
        if phase_err > np.pi:
            phase_err -= 2 * np.pi
        phase_err_deg = np.rad2deg(phase_err)

        # UP/DN duty
        if phase_err > 0:
            duty_up = min(abs(phase_err) / np.pi, 1.0)
            duty_dn = 0.0
        else:
            duty_up = 0.0
            duty_dn = min(abs(phase_err) / np.pi, 1.0)

        # Charge Pump
        i_pump = self.params.I_CP * (duty_up - duty_dn)

        # Loop Filter
        v_prop = i_pump * self.params.RZ
        self.v_int += i_pump * self.dt / self.params.CINT
        self.v_int = np.clip(self.v_int, -self.params.V_SUPPLY/2, self.params.V_SUPPLY/2)

        self.v_ctrl = self.params.V_SUPPLY / 2 + v_prop + self.v_int
        self.v_ctrl = np.clip(self.v_ctrl, 0.5, self.params.V_SUPPLY - 0.5)

        # VCO
        self.f_vco = self.f_ref + self.params.K_VCO * (self.v_ctrl - self.params.V_SUPPLY / 2)

        # Motor dynamics
        target_rpm = self.f_vco / self.params.NUM_BLADES * 60
        alpha = 1.0 - np.exp(-self.dt / self.params.TAU_MOTOR)
        self.rpm_follower += (target_rpm - self.rpm_follower) * alpha
        self.f_vco = self.rpm_follower / 60 * self.params.NUM_BLADES

        # Lock detector
        self.is_locked = abs(phase_err_deg) < self.params.LOCK_THRESHOLD

        # Update history
        self.time_history.append(self.t)
        self.phase_err_history.append(phase_err_deg)
        self.rpm_ref_history.append(self.ref_rpm)
        self.rpm_fb_history.append(self.rpm_follower)
        self.v_ctrl_history.append(self.v_ctrl)

        # Trim history
        if len(self.time_history) > self.history_len:
            self.time_history = self.time_history[-self.history_len:]
            self.phase_err_history = self.phase_err_history[-self.history_len:]
            self.rpm_ref_history = self.rpm_ref_history[-self.history_len:]
            self.rpm_fb_history = self.rpm_fb_history[-self.history_len:]
            self.v_ctrl_history = self.v_ctrl_history[-self.history_len:]

        self.t += self.dt

        return phase_err_deg

    def disturb(self):
        """Apply a disturbance to the follower"""
        self.rpm_follower += np.random.choice([-30, 30])
        self.phase_fb += np.random.uniform(-np.pi/2, np.pi/2)


# =============================================================================
# CANVAS RENDERER
# =============================================================================

class CanvasRenderer:
    """Renders simulation to HTML5 Canvas"""

    def __init__(self, canvas_id):
        self.canvas = document.getElementById(canvas_id)
        self.ctx = self.canvas.getContext("2d")
        self.width = self.canvas.width
        self.height = self.canvas.height

    def clear(self):
        self.ctx.fillStyle = "#1a1a2e"
        self.ctx.fillRect(0, 0, self.width, self.height)

    def draw_propellers(self, sim):
        """Draw the two propellers"""
        # Main propeller (left)
        cx1, cy1 = 150, 200
        self.draw_propeller(cx1, cy1, sim.phase_ref, "#4CAF50", "MAIN")

        # Follower propeller (right)
        cx2, cy2 = 350, 200
        color = "#00d26a" if sim.is_locked else "#e94560"
        self.draw_propeller(cx2, cy2, sim.phase_fb, color, "FOLLOWER")

        # Draw phase difference arc
        self.draw_phase_arc(250, 200, sim)

    def draw_propeller(self, cx, cy, phase, color, label):
        """Draw a 3-blade propeller"""
        radius = 60
        blade_width = 12

        # Draw hub
        self.ctx.beginPath()
        self.ctx.arc(cx, cy, 15, 0, 2 * np.pi)
        self.ctx.fillStyle = "#333"
        self.ctx.fill()
        self.ctx.strokeStyle = color
        self.ctx.lineWidth = 2
        self.ctx.stroke()

        # Draw 3 blades
        for i in range(3):
            angle = phase + i * 2 * np.pi / 3
            x1 = cx + 15 * np.cos(angle)
            y1 = cy + 15 * np.sin(angle)
            x2 = cx + radius * np.cos(angle)
            y2 = cy + radius * np.sin(angle)

            self.ctx.beginPath()
            self.ctx.moveTo(x1, y1)
            self.ctx.lineTo(x2, y2)
            self.ctx.strokeStyle = color
            self.ctx.lineWidth = blade_width
            self.ctx.lineCap = "round"
            self.ctx.stroke()

        # Label
        self.ctx.fillStyle = "#eee"
        self.ctx.font = "14px sans-serif"
        self.ctx.textAlign = "center"
        self.ctx.fillText(label, cx, cy + 90)

    def draw_phase_arc(self, cx, cy, sim):
        """Draw phase error visualization"""
        phase_err = (sim.phase_ref - sim.phase_fb) % (2 * np.pi)
        if phase_err > np.pi:
            phase_err -= 2 * np.pi

        # Draw arc showing phase difference
        self.ctx.beginPath()
        start = -np.pi/2
        end = start + phase_err
        self.ctx.arc(cx, cy, 30, min(start, end), max(start, end))
        self.ctx.strokeStyle = "#e94560" if abs(phase_err) > 0.035 else "#00d26a"
        self.ctx.lineWidth = 4
        self.ctx.stroke()

        # Phase error text
        self.ctx.fillStyle = "#eee"
        self.ctx.font = "12px sans-serif"
        self.ctx.textAlign = "center"
        err_deg = np.rad2deg(phase_err)
        self.ctx.fillText(f"Δφ = {err_deg:.1f}°", cx, cy + 50)

    def draw_plots(self, sim):
        """Draw time-series plots"""
        if len(sim.time_history) < 2:
            return

        plot_x = 500
        plot_width = self.width - plot_x - 50
        plot_height = 120

        # Phase error plot
        self.draw_line_plot(
            plot_x, 30, plot_width, plot_height,
            sim.phase_err_history, -180, 180,
            "#e94560", "Phase Error (°)"
        )

        # RPM plot
        self.draw_line_plot(
            plot_x, 180, plot_width, plot_height,
            sim.rpm_fb_history, 850, 950,
            "#4CAF50", "Follower RPM",
            reference=sim.ref_rpm
        )

        # Vctrl plot
        self.draw_line_plot(
            plot_x, 330, plot_width, plot_height,
            sim.v_ctrl_history, 0, 5,
            "#2196F3", "Vctrl (V)"
        )

    def draw_line_plot(self, x, y, w, h, data, y_min, y_max, color, label, reference=None):
        """Draw a line plot"""
        # Background
        self.ctx.fillStyle = "#16213e"
        self.ctx.fillRect(x, y, w, h)

        # Border
        self.ctx.strokeStyle = "#0f3460"
        self.ctx.lineWidth = 1
        self.ctx.strokeRect(x, y, w, h)

        # Reference line
        if reference is not None:
            ref_y = y + h - (reference - y_min) / (y_max - y_min) * h
            self.ctx.beginPath()
            self.ctx.moveTo(x, ref_y)
            self.ctx.lineTo(x + w, ref_y)
            self.ctx.strokeStyle = "#666"
            self.ctx.setLineDash([5, 5])
            self.ctx.stroke()
            self.ctx.setLineDash([])

        # Zero line for phase error
        if y_min < 0 < y_max:
            zero_y = y + h - (0 - y_min) / (y_max - y_min) * h
            self.ctx.beginPath()
            self.ctx.moveTo(x, zero_y)
            self.ctx.lineTo(x + w, zero_y)
            self.ctx.strokeStyle = "#444"
            self.ctx.stroke()

        # Data line
        if len(data) > 1:
            self.ctx.beginPath()
            for i, val in enumerate(data):
                px = x + (i / len(data)) * w
                py = y + h - (val - y_min) / (y_max - y_min) * h
                py = max(y, min(y + h, py))
                if i == 0:
                    self.ctx.moveTo(px, py)
                else:
                    self.ctx.lineTo(px, py)
            self.ctx.strokeStyle = color
            self.ctx.lineWidth = 2
            self.ctx.stroke()

        # Label
        self.ctx.fillStyle = "#aaa"
        self.ctx.font = "12px sans-serif"
        self.ctx.textAlign = "left"
        self.ctx.fillText(label, x + 5, y + 15)

    def draw_lock_indicator(self, sim):
        """Draw lock status LED"""
        cx, cy = 250, 320
        radius = 20

        self.ctx.beginPath()
        self.ctx.arc(cx, cy, radius, 0, 2 * np.pi)

        if sim.is_locked:
            self.ctx.fillStyle = "#00d26a"
            self.ctx.shadowColor = "#00d26a"
            self.ctx.shadowBlur = 20
        else:
            self.ctx.fillStyle = "#333"
            self.ctx.shadowBlur = 0

        self.ctx.fill()
        self.ctx.shadowBlur = 0

        # Label
        self.ctx.fillStyle = "#eee"
        self.ctx.font = "bold 14px sans-serif"
        self.ctx.textAlign = "center"
        label = "LOCKED" if sim.is_locked else "UNLOCKED"
        self.ctx.fillText(label, cx, cy + 40)


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class PySimulation:
    """Main simulation controller"""

    def __init__(self):
        self.sim = SynchrophaserSimulation()
        self.renderer = None
        self.interval_id = None

    def init(self):
        """Initialize after DOM is ready"""
        # Hide loading, show canvas
        loading_el = document.getElementById("loading")
        if loading_el:
            loading_el.style.display = "none"

        canvas = document.getElementById("sim-canvas")
        if not canvas:
            raise Exception("Canvas element 'sim-canvas' not found")

        canvas.style.display = "block"

        # Set canvas size - use fixed size if offsetWidth is 0
        canvas_width = canvas.offsetWidth
        if not canvas_width or canvas_width < 100:
            canvas_width = 1000
        canvas.width = canvas_width
        canvas.height = 480

        print(f"Canvas initialized: {canvas.width}x{canvas.height}")

        self.renderer = CanvasRenderer("sim-canvas")
        self.update_display()

        # Make available to JavaScript
        window.pySimulation = create_proxy(self)

        print("Synchrophaser PLL Simulation loaded!")

    def start(self):
        """Start the simulation loop"""
        if self.interval_id:
            clearInterval(self.interval_id)

        self.sim.running = True
        document.getElementById("start-btn").textContent = "Running..."
        document.getElementById("start-btn").disabled = True

        # Run at ~30 FPS
        def tick():
            if self.sim.running:
                # Run multiple sim steps per frame for speed
                for _ in range(5):
                    self.sim.step()
                self.update_display()

        self.interval_id = setInterval(create_proxy(tick), 33)

    def stop(self):
        """Stop the simulation"""
        self.sim.running = False
        if self.interval_id:
            clearInterval(self.interval_id)
            self.interval_id = None
        document.getElementById("start-btn").textContent = "Start Simulation"
        document.getElementById("start-btn").disabled = False

    def reset(self):
        """Reset the simulation"""
        self.stop()
        self.sim.reset()
        self.update_display()

    def disturb(self):
        """Apply a disturbance"""
        self.sim.disturb()

    def update_display(self):
        """Update the UI"""
        # Update status cards
        document.getElementById("rpm-main").textContent = f"{self.sim.ref_rpm:.0f}"
        document.getElementById("rpm-follower").textContent = f"{self.sim.rpm_follower:.0f}"

        if self.sim.phase_err_history:
            phase_err = self.sim.phase_err_history[-1]
            document.getElementById("phase-error").textContent = f"{phase_err:.1f}°"

        lock_card = document.getElementById("lock-status")
        if self.sim.is_locked:
            lock_card.classList.add("locked")
            lock_card.querySelector(".value").textContent = "LOCKED"
        else:
            lock_card.classList.remove("locked")
            lock_card.querySelector(".value").textContent = "UNLOCKED"

        # Render canvas
        if self.renderer:
            self.renderer.clear()
            self.renderer.draw_propellers(self.sim)
            self.renderer.draw_plots(self.sim)
            self.renderer.draw_lock_indicator(self.sim)


# Initialize when PyScript loads
print("=== Synchrophaser PLL Simulation Module Loaded ===")

def main():
    """Main entry point with error handling"""
    print("main() called")
    try:
        print("Step 1: Creating PySimulation instance...")
        app = PySimulation()
        print("Step 2: Calling app.init()...")
        app.init()
        print("Step 3: Simulation initialized successfully!")
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"ERROR: {error_msg}")
        # Show error in loading div
        try:
            loading = document.getElementById("loading")
            if loading:
                loading.innerHTML = f'''
                    <div style="text-align:left; padding:20px;">
                    <p style="color: #e94560; font-weight:bold;">Error loading simulation:</p>
                    <pre style="font-size: 0.7rem; color: #aaa; white-space:pre-wrap; margin-top:10px;">{error_msg}</pre>
                    <p style="font-size: 0.8rem; margin-top: 1rem;">Check browser console (F12) for details</p>
                    </div>
                '''
        except Exception as e2:
            print(f"Could not update loading div: {e2}")
        raise

# Run initialization
print("About to call main()...")
main()
print("main() completed")
