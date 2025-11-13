"""
Kalman filter for optimal blade phase estimation.

Estimates propeller blade phase from noisy angle measurements.
Used in advanced synchrophaser for improved phase tracking.

Based on standard Kalman filter theory (Kalman 1960, Welch & Bishop 2006).
"""

import numpy as np


class PhaseKalmanFilter:
    """
    Kalman filter for estimating blade phase and phase rate.

    State vector: [phase, phase_rate]
    - phase: Blade angle (radians, wrapped to [-π, π])
    - phase_rate: Angular velocity difference (rad/s)

    Measurement: Raw blade angle from encoder

    This is a LINEAR Kalman filter with constant matrices.
    Suitable for real-time embedded systems (low computational cost).
    """

    def __init__(
        self,
        process_noise_phase: float = 0.001,   # rad²/s (how much phase wanders)
        process_noise_rate: float = 0.01,     # (rad/s)²/s (rate variations)
        measurement_noise: float = 0.02,       # rad² (sensor noise)
        initial_phase: float = 0.0,
        initial_rate: float = 0.0,
    ):
        """
        Initialize Kalman filter.

        Args:
            process_noise_phase: Process noise for phase (rad²/s)
            process_noise_rate: Process noise for phase rate ((rad/s)²/s)
            measurement_noise: Measurement noise variance (rad²)
            initial_phase: Initial phase estimate (radians)
            initial_rate: Initial phase rate estimate (rad/s)
        """
        # State vector: [phase, phase_rate]
        self.x = np.array([initial_phase, initial_rate], dtype=np.float64)

        # State covariance matrix (uncertainty in estimates)
        self.P = np.array([
            [0.1, 0.0],   # Initial uncertainty in phase
            [0.0, 0.1]    # Initial uncertainty in rate
        ], dtype=np.float64)

        # Process noise covariance matrix Q
        self.Q = np.array([
            [process_noise_phase, 0.0],
            [0.0, process_noise_rate]
        ], dtype=np.float64)

        # Measurement noise covariance (scalar, measures phase only)
        self.R = measurement_noise

        # Measurement matrix H: we measure phase only (not rate)
        # measurement = H @ state = [1, 0] @ [phase, rate] = phase
        self.H = np.array([1.0, 0.0], dtype=np.float64)

        # Statistics for monitoring
        self.innovation = 0.0  # Last measurement - prediction
        self.innovation_variance = 0.0
        self.update_count = 0

    def predict(self, dt: float) -> None:
        """
        Prediction step: propagate state forward in time.

        State dynamics:
            phase(t+dt) = phase(t) + phase_rate(t) * dt
            phase_rate(t+dt) = phase_rate(t)  (assumed constant + noise)

        Args:
            dt: Time step (seconds)
        """
        # State transition matrix F
        # x_next = F @ x_current
        F = np.array([
            [1.0, dt],    # phase_next = phase + rate*dt
            [0.0, 1.0]    # rate_next = rate (constant velocity model)
        ], dtype=np.float64)

        # Predict state: x_pred = F @ x
        self.x = F @ self.x

        # Wrap phase to [-π, π] after prediction
        self.x[0] = np.arctan2(np.sin(self.x[0]), np.cos(self.x[0]))

        # Predict covariance: P_pred = F @ P @ F^T + Q
        self.P = F @ self.P @ F.T + self.Q * dt  # Q scaled by dt

    def update(self, measured_phase: float) -> None:
        """
        Update step: incorporate new measurement.

        Args:
            measured_phase: Measured blade angle (radians)
        """
        # Wrap measurement to [-π, π]
        measured_phase = np.arctan2(np.sin(measured_phase), np.cos(measured_phase))

        # Innovation (measurement residual)
        # y = z - H @ x
        predicted_measurement = self.H @ self.x  # Predicted phase
        innovation = measured_phase - predicted_measurement

        # Wrap innovation to [-π, π] (handle phase wrap-around)
        innovation = np.arctan2(np.sin(innovation), np.cos(innovation))

        # Innovation covariance
        # S = H @ P @ H^T + R
        S = self.H @ self.P @ self.H.T + self.R
        self.innovation_variance = S

        # Kalman gain
        # K = P @ H^T @ S^(-1)
        K = self.P @ self.H.T / S  # Division since S is scalar

        # Update state estimate
        # x = x + K * y
        self.x = self.x + K * innovation

        # Wrap phase after update
        self.x[0] = np.arctan2(np.sin(self.x[0]), np.cos(self.x[0]))

        # Update covariance
        # P = (I - K @ H) @ P
        I_KH = np.eye(2) - np.outer(K, self.H)
        self.P = I_KH @ self.P

        # Store statistics
        self.innovation = innovation
        self.update_count += 1

    def filter(self, measured_phase: float, dt: float) -> tuple[float, float]:
        """
        Complete filter cycle: predict + update.

        Args:
            measured_phase: Measured blade angle (radians)
            dt: Time step since last filter call (seconds)

        Returns:
            Tuple of (filtered_phase, filtered_phase_rate)
        """
        if dt > 0:
            self.predict(dt)
        self.update(measured_phase)

        return self.x[0], self.x[1]

    def get_phase_estimate(self) -> float:
        """Get current phase estimate (radians)."""
        return self.x[0]

    def get_phase_rate_estimate(self) -> float:
        """Get current phase rate estimate (rad/s)."""
        return self.x[1]

    def get_phase_uncertainty(self) -> float:
        """Get uncertainty (standard deviation) in phase estimate (radians)."""
        return np.sqrt(self.P[0, 0])

    def reset(self, phase: float = 0.0, rate: float = 0.0) -> None:
        """
        Reset filter to initial conditions.

        Args:
            phase: Initial phase estimate (radians)
            rate: Initial phase rate estimate (rad/s)
        """
        self.x = np.array([phase, rate], dtype=np.float64)
        self.P = np.array([
            [0.1, 0.0],
            [0.0, 0.1]
        ], dtype=np.float64)
        self.innovation = 0.0
        self.update_count = 0

    def get_stats(self) -> dict:
        """
        Get filter statistics for monitoring/debugging.

        Returns:
            Dictionary with filter state and performance metrics
        """
        return {
            'phase_est': self.x[0],
            'phase_rate_est': self.x[1],
            'phase_std': np.sqrt(self.P[0, 0]),
            'rate_std': np.sqrt(self.P[1, 1]),
            'innovation': self.innovation,
            'innovation_std': np.sqrt(self.innovation_variance),
            'update_count': self.update_count,
        }

    def __repr__(self):
        return (
            f"PhaseKalmanFilter(phase={self.x[0]:.4f} rad, "
            f"rate={self.x[1]:.4f} rad/s, "
            f"phase_std={np.sqrt(self.P[0, 0]):.4f} rad)"
        )


def test_kalman_filter():
    """Basic test of Kalman filter functionality."""
    print("Testing PhaseKalmanFilter...")

    # Create filter
    kf = PhaseKalmanFilter(
        process_noise_phase=0.001,
        process_noise_rate=0.01,
        measurement_noise=0.02,
    )

    # Simulate noisy measurements
    dt = 0.01  # 100 Hz
    true_phase_rate = 0.1  # rad/s (slow drift)
    measurement_noise_std = 0.14  # rad (~8°)

    true_phase = 0.0
    for i in range(100):
        # Generate true phase
        true_phase += true_phase_rate * dt
        true_phase = np.arctan2(np.sin(true_phase), np.cos(true_phase))

        # Add measurement noise
        measured = true_phase + np.random.normal(0, measurement_noise_std)

        # Filter
        filt_phase, filt_rate = kf.filter(measured, dt)

        if i % 20 == 0:
            error = abs(filt_phase - true_phase)
            print(f"  t={i*dt:.2f}s: true={true_phase:.3f}, "
                  f"meas={measured:.3f}, filt={filt_phase:.3f}, "
                  f"error={error:.4f} rad")

    stats = kf.get_stats()
    print(f"\nFinal stats:")
    print(f"  Phase estimate: {stats['phase_est']:.4f} rad")
    print(f"  Phase uncertainty: {stats['phase_std']:.4f} rad")
    print(f"  Rate estimate: {stats['phase_rate_est']:.4f} rad/s")
    print(f"  True rate: {true_phase_rate:.4f} rad/s")

    print("\n✓ Kalman filter test complete")


if __name__ == '__main__':
    test_kalman_filter()
