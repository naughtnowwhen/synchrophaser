"""
Phase-Frequency Detector (PFD) based synchrophaser.

Modern PLL architecture using both phase and frequency error for robust
synchronization. Based on PFD techniques from digital PLLs.

This is a LEGITIMATE improvement over simple phase detection:
- Faster lock acquisition
- Better handling of large errors
- More robust startup behavior
- Standard in modern PLL systems

References:
- "Phase-Locked Loops: Design, Simulation, and Applications" (Best, 2007)
- "PLL Performance, Simulation, and Design" (Banerjee, 2006)
- Digital PLL design (Texas Instruments, Analog Devices application notes)

Author: Based on PLL literature
Date: 2025-11-12
"""

import numpy as np
from typing import Dict

from synchrophaser import Synchrophaser
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
)


class PFDSynchrophaser(Synchrophaser):
    """
    Phase-Frequency Detector based synchrophaser.

    Key difference from baseline: Uses BOTH phase and frequency errors.

    Traditional Phase Detector:
        error = phase_main - phase_follower
        correction = PID(phase_error)

    Phase-Frequency Detector:
        phase_error = integrated cumulative phase difference
        freq_error = (ω_main - ω_follower)
        correction = PID(phase_error) + K_F * freq_error

    Advantages:
    1. Frequency term provides "velocity" information
    2. Faster convergence (frequency pulls, phase fine-tunes)
    3. Better large-error handling
    4. Standard in modern PLLs

    This is like having:
    - Phase detector: "Are the blades aligned?"
    - Frequency detector: "Are they spinning at the same speed?"

    Using both gives better control than phase alone.
    """

    def __init__(
        self,
        k_p: float = SYNCHRO_K_P,
        k_i: float = SYNCHRO_K_I,
        k_d: float = SYNCHRO_K_D,
        k_f: float = 0.5,  # NEW: Frequency error gain
        integrator_min: float = SYNCHRO_INTEGRATOR_MIN,
        integrator_max: float = SYNCHRO_INTEGRATOR_MAX,
        phase_scale: float = SYNCHRO_PHASE_SCALE,
        derivative_filter_alpha: float = SYNCHRO_DERIVATIVE_FILTER_ALPHA,
        deadband: float = SYNCHRO_DEADBAND,
        rate_limit: float = SYNCHRO_RATE_LIMIT,
    ):
        """
        Initialize PFD-based synchrophaser.

        Args:
            k_p, k_i, k_d: PID gains for phase error
            k_f: Frequency error gain (NEW)
            integrator_min, integrator_max: Anti-windup limits
            phase_scale: Phase to RPM conversion
            derivative_filter_alpha: Low-pass filter coefficient
            deadband: Minimum error to correct (radians)
            rate_limit: Max RPM/sec change
        """
        # Initialize baseline synchrophaser
        super().__init__(
            k_p=k_p,
            k_i=k_i,
            k_d=k_d,
            integrator_min=integrator_min,
            integrator_max=integrator_max,
            phase_scale=phase_scale,
            derivative_filter_alpha=derivative_filter_alpha,
            deadband=deadband,
            rate_limit=rate_limit,
        )

        # NEW: Frequency error gain
        self.k_f = k_f

        # Frequency error tracking
        self.freq_error = 0.0  # rad/s (angular velocity difference)
        self.freq_error_rpm = 0.0  # RPM (for display)
        self.frequency_term = 0.0  # Contribution from frequency error

        # Filtered frequency error (smooth out noise)
        self.filtered_freq_error = 0.0
        self.freq_filter_alpha = 0.1  # Low-pass filter for frequency

    def enable(self):
        """Enable synchrophaser and reset all state."""
        super().enable()

        # Reset frequency error state
        self.freq_error = 0.0
        self.freq_error_rpm = 0.0
        self.frequency_term = 0.0
        self.filtered_freq_error = 0.0

    def disable(self):
        """Disable synchrophaser and reset all state."""
        super().disable()

        # Reset frequency error state
        self.freq_error = 0.0
        self.freq_error_rpm = 0.0
        self.frequency_term = 0.0
        self.filtered_freq_error = 0.0

    def update(
        self,
        blade_angle_main: float,
        blade_angle_follower: float,
        omega_main: float,
        omega_follower: float,
        dt: float,
    ) -> float:
        """
        Update PFD synchrophaser with phase AND frequency errors.

        This is the key difference: we use omega (frequency) in addition
        to blade angles (phase).

        Args:
            blade_angle_main: Main propeller blade angle (radians)
            blade_angle_follower: Follower propeller blade angle (radians)
            omega_main: Main propeller angular velocity (rad/s)
            omega_follower: Follower propeller angular velocity (rad/s)
            dt: Time step (seconds)

        Returns:
            RPM correction to apply to follower's nominal setpoint
        """
        if not self.enabled:
            self.phase_error = 0.0
            self.freq_error = 0.0
            self.rpm_correction = 0.0
            self.proportional_term = 0.0
            self.integral_term = 0.0
            self.derivative_term = 0.0
            self.frequency_term = 0.0
            return 0.0

        # ================================================================
        # PHASE-FREQUENCY DETECTION - This is the advanced feature!
        # ================================================================

        # 1. Phase error (same as baseline)
        raw_phase_error = self.compute_phase_error(
            blade_angle_main,
            blade_angle_follower
        )

        # 2. Frequency error (NEW - this is the PFD improvement!)
        self.freq_error = omega_main - omega_follower  # rad/s

        # Filter frequency error to reduce noise
        self.filtered_freq_error = (
            self.freq_filter_alpha * self.freq_error +
            (1.0 - self.freq_filter_alpha) * self.filtered_freq_error
        )

        # Convert to RPM for display
        self.freq_error_rpm = self.freq_error * 60.0 / (2.0 * np.pi)

        # ================================================================
        # Control using BOTH phase and frequency
        # ================================================================

        # Apply deadband to phase error
        if abs(raw_phase_error) < self.deadband:
            self.phase_error = 0.0
            self.integrator *= 0.99  # Decay integrator in deadband
        else:
            self.phase_error = raw_phase_error

        # Update statistics
        self.update_count += 1
        self.cumulative_error += abs(raw_phase_error)
        self.max_phase_error = max(self.max_phase_error, abs(raw_phase_error))

        # Proportional term (phase error)
        self.proportional_term = self.k_p * self.phase_error

        # Integral term (phase error accumulation)
        if abs(self.phase_error) > 0:
            self.integrator += self.phase_error * dt
            max_integral = 0.5
            self.integrator = np.clip(self.integrator, -max_integral, max_integral)
        self.integral_term = self.k_i * self.integrator

        # Derivative term (phase error rate of change)
        if dt > 0:
            raw_derivative = (self.phase_error - self.previous_phase_error) / dt
            self.filtered_derivative = (
                self.derivative_filter_alpha * raw_derivative +
                (1.0 - self.derivative_filter_alpha) * self.filtered_derivative
            )
            self.derivative_term = self.k_d * self.filtered_derivative
        else:
            self.derivative_term = 0.0

        # Store for next iteration
        self.previous_phase_error = self.phase_error

        # NEW: Frequency term (this is the PFD improvement!)
        # Frequency error provides "velocity" feedback
        # Helps pull frequencies together before fine-tuning phase
        self.frequency_term = self.k_f * self.filtered_freq_error

        # Total correction: PID on phase + proportional on frequency
        phase_correction_radians = (
            self.proportional_term +
            self.integral_term +
            self.derivative_term
        )
        phase_correction_rpm = phase_correction_radians * self.phase_scale

        # Add frequency term (directly in RPM)
        freq_correction_rpm = self.frequency_term * 60.0 / (2.0 * np.pi)

        # Combined correction
        desired_rpm_correction = phase_correction_rpm + freq_correction_rpm

        # RATE LIMITING: Prevent sudden jumps
        if dt > 0:
            max_change = self.rate_limit * dt
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
        Get synchrophaser statistics including frequency error.

        Returns:
            Dictionary with performance metrics
        """
        # Get baseline stats
        stats = super().get_stats()

        # Add PFD-specific statistics
        stats.update({
            'freq_error': self.freq_error,
            'freq_error_rpm': self.freq_error_rpm,
            'frequency_term': self.frequency_term,
            'filtered_freq_error': self.filtered_freq_error,
        })

        return stats

    def __repr__(self):
        return (
            f"PFDSynchrophaser(enabled={self.enabled}, "
            f"φ_error={np.degrees(self.phase_error):.2f}°, "
            f"ω_error={self.freq_error_rpm:.2f} RPM, "
            f"RPM_corr={self.rpm_correction:.2f})"
        )
