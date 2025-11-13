"""
Synchrophaser system for twin propellers using Phase-Locked Loop (PLL) control.

Phase 3: Implements modern synchrophaser with Proportional-Integral (PI) controller
to minimize phase error between main and follower propellers.

Based on research:
- PLL-based phase error detection
- PI controller for steady-state error elimination
- Anti-windup integrator limiting
- Main/follower architecture
"""

import numpy as np
from typing import Tuple, Dict

from parameters import (
    SYNCHRO_K_P,
    SYNCHRO_K_I,
    SYNCHRO_K_D,
    SYNCHRO_INTEGRATOR_MIN,
    SYNCHRO_INTEGRATOR_MAX,
    SYNCHRO_PHASE_SCALE,
    SYNCHRO_DERIVATIVE_FILTER_ALPHA,
    SYNCHRO_DEADBAND,
    SYNCHRO_RATE_LIMIT,
    TEST_MODE_DURATION,
)


class Synchrophaser:
    """
    Phase-Locked Loop (PLL) based synchrophaser for twin propellers.

    The synchrophaser measures phase error between main and follower propellers
    and adjusts the follower's RPM setpoint to minimize this error.

    Control Strategy:
        1. Measure phase error: φ_error = φ_main - φ_follower
        2. PI controller: correction = K_P * φ_error + K_I * ∫φ_error dt
        3. Adjust follower RPM setpoint: RPM_follower = RPM_nominal + correction

    This is analogous to a PLL in electrical systems, where we're "locking"
    the follower's phase to the main propeller's phase.
    """

    def __init__(
        self,
        k_p: float = SYNCHRO_K_P,
        k_i: float = SYNCHRO_K_I,
        k_d: float = SYNCHRO_K_D,
        integrator_min: float = SYNCHRO_INTEGRATOR_MIN,
        integrator_max: float = SYNCHRO_INTEGRATOR_MAX,
        phase_scale: float = SYNCHRO_PHASE_SCALE,
        derivative_filter_alpha: float = SYNCHRO_DERIVATIVE_FILTER_ALPHA,
        deadband: float = SYNCHRO_DEADBAND,
        rate_limit: float = SYNCHRO_RATE_LIMIT,
    ):
        """
        Initialize synchrophaser with PID control and anti-overshoot features.

        Args:
            k_p: Proportional gain (reacts to current error)
            k_i: Integral gain (eliminates steady-state error)
            k_d: Derivative gain (dampens oscillations)
            integrator_min: Lower limit for integrator (anti-windup)
            integrator_max: Upper limit for integrator (anti-windup)
            phase_scale: Scaling factor for phase→RPM conversion
            derivative_filter_alpha: Low-pass filter coefficient for derivative (0-1)
            deadband: Ignore errors smaller than this (radians)
            rate_limit: Max RPM/sec change in correction
        """
        # Control gains (PID)
        self.k_p = k_p
        self.k_i = k_i
        self.k_d = k_d
        self.phase_scale = phase_scale

        # Anti-overshoot parameters
        self.derivative_filter_alpha = derivative_filter_alpha
        self.deadband = deadband
        self.rate_limit = rate_limit

        # Integrator state and limits (anti-windup)
        self.integrator = 0.0
        self.integrator_min = integrator_min
        self.integrator_max = integrator_max

        # State tracking
        self.enabled = False
        self.phase_error = 0.0  # radians
        self.previous_phase_error = 0.0  # For derivative term
        self.filtered_derivative = 0.0  # Smoothed derivative to reduce noise
        self.previous_rpm_correction = 0.0  # For rate limiting
        self.rpm_correction = 0.0  # RPM
        self.proportional_term = 0.0
        self.integral_term = 0.0
        self.derivative_term = 0.0

        # Statistics (for testing/analysis)
        self.max_phase_error = 0.0
        self.cumulative_error = 0.0
        self.update_count = 0

    def enable(self):
        """Enable synchrophaser (activate phase locking)."""
        self.enabled = True
        # Reset all state to prevent startup transients
        self.integrator = 0.0
        self.phase_error = 0.0
        self.previous_phase_error = 0.0
        self.filtered_derivative = 0.0
        self.previous_rpm_correction = 0.0

    def disable(self):
        """Disable synchrophaser (propellers run independently)."""
        self.enabled = False
        # Reset all state when disabled
        self.integrator = 0.0
        self.phase_error = 0.0
        self.previous_phase_error = 0.0
        self.filtered_derivative = 0.0
        self.previous_rpm_correction = 0.0

    def reset_stats(self):
        """Reset statistics counters."""
        self.max_phase_error = 0.0
        self.cumulative_error = 0.0
        self.update_count = 0
        self.integrator = 0.0

    def compute_phase_error(
        self,
        blade_angle_main: float,
        blade_angle_follower: float,
    ) -> float:
        """
        Compute TRUE phase error from actual blade positions.

        This is the real synchrophaser magic - we measure the actual
        angular difference between blade #1 on each propeller.

        Args:
            blade_angle_main: Main propeller blade #1 angle (0-2π radians)
            blade_angle_follower: Follower propeller blade #1 angle (0-2π radians)

        Returns:
            Phase error in radians, wrapped to [-π, π]
            Positive error means main is ahead, follower needs to speed up
        """
        # Compute raw phase difference
        raw_error = blade_angle_main - blade_angle_follower

        # Wrap to [-π, π] for cyclic phase
        # This is critical because 350° - 10° should be -20°, not +340°
        phase_error = np.arctan2(np.sin(raw_error), np.cos(raw_error))

        return phase_error

    def update(
        self,
        blade_angle_main: float,
        blade_angle_follower: float,
        dt: float,
    ) -> float:
        """
        Update synchrophaser and compute RPM correction for follower.

        Uses TRUE PHASE ERROR from blade positions with PID control
        PLUS anti-overshoot features: derivative filtering, deadband, rate limiting.

        Args:
            blade_angle_main: Main propeller blade #1 angle (0-2π radians)
            blade_angle_follower: Follower propeller blade #1 angle (0-2π radians)
            dt: Time step (seconds)

        Returns:
            RPM correction to apply to follower's nominal setpoint
            (0 if synchrophaser is disabled)
        """
        if not self.enabled:
            self.phase_error = 0.0
            self.rpm_correction = 0.0
            self.proportional_term = 0.0
            self.integral_term = 0.0
            self.derivative_term = 0.0
            return 0.0

        # Compute TRUE phase error from actual blade positions
        raw_phase_error = self.compute_phase_error(blade_angle_main, blade_angle_follower)

        # DEADBAND: Ignore very small errors to reduce jitter
        if abs(raw_phase_error) < self.deadband:
            # Error is tiny - don't correct, let integrator decay slightly
            self.phase_error = 0.0
            # Slowly decay integrator toward zero when in deadband
            self.integrator *= 0.99
        else:
            self.phase_error = raw_phase_error

        # Update statistics (use raw error, not deadband-filtered)
        self.update_count += 1
        self.cumulative_error += abs(raw_phase_error)
        self.max_phase_error = max(self.max_phase_error, abs(raw_phase_error))

        # Proportional term (reacts to current phase error)
        self.proportional_term = self.k_p * self.phase_error

        # Integral term (eliminates steady-state error)
        # Only integrate when outside deadband
        if abs(self.phase_error) > 0:
            self.integrator += self.phase_error * dt
            # Anti-windup: clamp integrator tightly
            max_integral = 0.5  # Tight limit (radians * seconds)
            self.integrator = np.clip(self.integrator, -max_integral, max_integral)
        self.integral_term = self.k_i * self.integrator

        # Derivative term with LOW-PASS FILTER to reduce noise amplification
        if dt > 0:
            # Compute raw derivative
            raw_derivative = (self.phase_error - self.previous_phase_error) / dt

            # Apply exponential moving average filter
            # filtered = alpha * raw + (1-alpha) * previous
            # Low alpha (e.g., 0.1) = heavy smoothing, slow response
            self.filtered_derivative = (
                self.derivative_filter_alpha * raw_derivative +
                (1.0 - self.derivative_filter_alpha) * self.filtered_derivative
            )

            # Use filtered derivative (much smoother!)
            self.derivative_term = self.k_d * self.filtered_derivative
        else:
            self.derivative_term = 0.0

        # Store for next iteration
        self.previous_phase_error = self.phase_error

        # Full PID correction: convert phase error (radians) to RPM correction
        phase_correction_radians = self.proportional_term + self.integral_term + self.derivative_term
        desired_rpm_correction = phase_correction_radians * self.phase_scale

        # RATE LIMITING: Prevent sudden jumps in correction
        if dt > 0:
            max_change = self.rate_limit * dt  # Max change per timestep
            correction_delta = desired_rpm_correction - self.previous_rpm_correction
            correction_delta = np.clip(correction_delta, -max_change, max_change)
            self.rpm_correction = self.previous_rpm_correction + correction_delta
        else:
            self.rpm_correction = desired_rpm_correction

        # Final safety limit
        self.rpm_correction = np.clip(self.rpm_correction, -15.0, 15.0)

        # Store for next iteration
        self.previous_rpm_correction = self.rpm_correction

        return self.rpm_correction

    def get_stats(self) -> Dict[str, float]:
        """
        Get synchrophaser statistics.

        Returns:
            Dictionary with performance metrics
        """
        if self.update_count == 0:
            mean_error = 0.0
        else:
            mean_error = self.cumulative_error / self.update_count

        return {
            'enabled': self.enabled,
            'phase_error': self.phase_error,
            'phase_error_deg': np.degrees(self.phase_error),
            'rpm_correction': self.rpm_correction,
            'proportional_term': self.proportional_term,
            'integral_term': self.integral_term,
            'integrator': self.integrator,
            'max_phase_error': self.max_phase_error,
            'max_phase_error_deg': np.degrees(self.max_phase_error),
            'mean_abs_error': mean_error,
            'mean_abs_error_deg': np.degrees(mean_error),
            'update_count': self.update_count,
        }

    def __repr__(self):
        return (
            f"Synchrophaser(enabled={self.enabled}, "
            f"φ_error={np.degrees(self.phase_error):.2f}°, "
            f"RPM_corr={self.rpm_correction:.2f})"
        )


class SynchrophaserTester:
    """
    Systematic testing framework for synchrophaser effectiveness.

    Runs controlled tests with synchrophaser ON and OFF, collecting metrics
    to quantify performance improvement.
    """

    def __init__(self):
        """Initialize tester."""
        self.is_testing = False
        self.test_phase = None  # 'off', 'on', or 'complete'
        self.phase_start_time = 0.0

        # Metrics for OFF phase
        self.off_rpm_errors = []
        self.off_phase_errors = []

        # Metrics for ON phase
        self.on_rpm_errors = []
        self.on_phase_errors = []

        # Test results
        self.results = None

    def start_test(self, current_time: float):
        """Start a new test cycle."""
        self.is_testing = True
        self.test_phase = 'off'
        self.phase_start_time = current_time

        # Clear previous data
        self.off_rpm_errors = []
        self.off_phase_errors = []
        self.on_rpm_errors = []
        self.on_phase_errors = []
        self.results = None

    def update(
        self,
        current_time: float,
        rpm_main: float,
        rpm_follower: float,
        phase_error: float,
        test_duration: float,
    ) -> Tuple[bool, str]:
        """
        Update test state and collect metrics.

        Args:
            current_time: Current simulation time
            rpm_main: Main propeller RPM
            rpm_follower: Follower propeller RPM
            phase_error: Phase error in radians
            test_duration: Duration for each phase (OFF and ON)

        Returns:
            Tuple of (synchrophaser_should_be_enabled, status_message)
        """
        if not self.is_testing:
            return False, "Not testing"

        elapsed = current_time - self.phase_start_time
        rpm_error = abs(rpm_main - rpm_follower)

        # Collect metrics for current phase
        if self.test_phase == 'off':
            self.off_rpm_errors.append(rpm_error)
            self.off_phase_errors.append(abs(phase_error))

            if elapsed >= test_duration:
                # Switch to ON phase
                self.test_phase = 'on'
                self.phase_start_time = current_time
                return True, f"Test: OFF complete, switching to ON..."

            return False, f"Test: Synchro OFF ({elapsed:.1f}/{test_duration:.0f}s)"

        elif self.test_phase == 'on':
            self.on_rpm_errors.append(rpm_error)
            self.on_phase_errors.append(abs(phase_error))

            if elapsed >= test_duration:
                # Test complete - compute results
                self._compute_results()
                self.test_phase = 'complete'
                self.is_testing = False
                return True, "Test: COMPLETE! See results below."

            return True, f"Test: Synchro ON ({elapsed:.1f}/{test_duration:.0f}s)"

        return False, "Test complete"

    def _compute_results(self):
        """Compute test results comparing OFF vs ON performance."""
        self.results = {
            # OFF metrics
            'off_mean_rpm_error': np.mean(self.off_rpm_errors),
            'off_max_rpm_error': np.max(self.off_rpm_errors),
            'off_std_rpm_error': np.std(self.off_rpm_errors),
            'off_mean_phase_error_deg': np.degrees(np.mean(self.off_phase_errors)),
            'off_max_phase_error_deg': np.degrees(np.max(self.off_phase_errors)),

            # ON metrics
            'on_mean_rpm_error': np.mean(self.on_rpm_errors),
            'on_max_rpm_error': np.max(self.on_rpm_errors),
            'on_std_rpm_error': np.std(self.on_rpm_errors),
            'on_mean_phase_error_deg': np.degrees(np.mean(self.on_phase_errors)),
            'on_max_phase_error_deg': np.degrees(np.max(self.on_phase_errors)),

            # Improvement metrics
            'rpm_error_improvement_pct': 0.0,
            'phase_error_improvement_pct': 0.0,
        }

        # Calculate improvement percentages
        if self.results['off_mean_rpm_error'] > 0:
            improvement = (
                (self.results['off_mean_rpm_error'] - self.results['on_mean_rpm_error'])
                / self.results['off_mean_rpm_error'] * 100
            )
            self.results['rpm_error_improvement_pct'] = improvement

        if self.results['off_mean_phase_error_deg'] > 0:
            improvement = (
                (self.results['off_mean_phase_error_deg'] - self.results['on_mean_phase_error_deg'])
                / self.results['off_mean_phase_error_deg'] * 100
            )
            self.results['phase_error_improvement_pct'] = improvement

    def get_results_string(self) -> str:
        """Format test results as readable string."""
        if not self.results:
            return "No test results available"

        r = self.results
        return f"""
╔══════════════════════════════════════════════════════════╗
║           SYNCHROPHASER TEST RESULTS                     ║
╚══════════════════════════════════════════════════════════╝

📊 RPM Error (Main vs Follower):
  OFF:  Mean={r['off_mean_rpm_error']:.2f} RPM, Max={r['off_max_rpm_error']:.2f} RPM, Std={r['off_std_rpm_error']:.2f}
  ON:   Mean={r['on_mean_rpm_error']:.2f} RPM, Max={r['on_max_rpm_error']:.2f} RPM, Std={r['on_std_rpm_error']:.2f}
  Improvement: {r['rpm_error_improvement_pct']:.1f}% reduction ✓

📐 Phase Error:
  OFF:  Mean={r['off_mean_phase_error_deg']:.2f}°, Max={r['off_max_phase_error_deg']:.2f}°
  ON:   Mean={r['on_mean_phase_error_deg']:.2f}°, Max={r['on_max_phase_error_deg']:.2f}°
  Improvement: {r['phase_error_improvement_pct']:.1f}% reduction ✓

{'✅ SYNCHROPHASER EFFECTIVE!' if r['rpm_error_improvement_pct'] > 20 else '⚠️  Marginal improvement' if r['rpm_error_improvement_pct'] > 0 else '❌ No improvement'}
"""

    def get_results_clipboard(self) -> str:
        """Get results formatted for clipboard sharing."""
        if not self.results:
            return "No test results available"

        r = self.results
        return f"""SYNCHROPHASER TEST RESULTS
Duration: {TEST_MODE_DURATION}s each phase

RPM ERROR (Main vs Follower):
Synchro OFF:
- Mean: {r['off_mean_rpm_error']:.2f} RPM
- Max:  {r['off_max_rpm_error']:.2f} RPM
- Std:  {r['off_std_rpm_error']:.2f} RPM

Synchro ON:
- Mean: {r['on_mean_rpm_error']:.2f} RPM
- Max:  {r['on_max_rpm_error']:.2f} RPM
- Std:  {r['on_std_rpm_error']:.2f} RPM

IMPROVEMENT: {r['rpm_error_improvement_pct']:.1f}% reduction in mean RPM error

PHASE ERROR:
OFF: Mean={r['off_mean_phase_error_deg']:.2f}°, Max={r['off_max_phase_error_deg']:.2f}°
ON:  Mean={r['on_mean_phase_error_deg']:.2f}°, Max={r['on_max_phase_error_deg']:.2f}°

STATUS: {'EFFECTIVE (>20% improvement)' if r['rpm_error_improvement_pct'] > 20 else 'MARGINAL (0-20% improvement)' if r['rpm_error_improvement_pct'] > 0 else 'NOT WORKING (negative improvement)'}

Control Parameters:
- K_P: {SYNCHRO_K_P}
- K_I: {SYNCHRO_K_I}
- Algorithm: RPM-based PI controller
"""
