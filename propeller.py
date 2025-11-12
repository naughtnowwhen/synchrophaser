"""
Propeller dynamics with simple governor control.

Phase 2: Single propeller responding to atmospheric density variations.
The propeller attempts to maintain constant RPM but varies with local air density.
"""

import numpy as np
from typing import Optional

from parameters import (
    PROPELLER_X_DEFAULT,
    PROPELLER_Y_DEFAULT,
    PROPELLER_INERTIA,
    PROPELLER_RPM_NOMINAL,
    K_AERO,
    GOVERNOR_K_P,
    GOVERNOR_BASE_TORQUE,
    RHO_SEA_LEVEL,
)


class Propeller:
    """
    Single propeller with aerodynamic loading and governor control.

    The propeller experiences varying aerodynamic torque based on local
    atmospheric density, and a simple proportional governor attempts to
    maintain constant RPM by adjusting engine torque.

    Physics:
        I * dω/dt = Q_engine - Q_aero
        Q_aero = k_aero * ρ_local * ω²
        Q_engine = Q_base + K_P * (ω_target - ω)  [governor]

    Key interface for visualization:
        propeller.update(dt, sim_time, density_field)
    """

    def __init__(
        self,
        x: float = PROPELLER_X_DEFAULT,
        y: float = PROPELLER_Y_DEFAULT,
        inertia: float = PROPELLER_INERTIA,
        rpm_nominal: float = PROPELLER_RPM_NOMINAL,
        k_aero: float = K_AERO,
        governor_kp: float = GOVERNOR_K_P,
        base_torque: float = GOVERNOR_BASE_TORQUE,
    ):
        """
        Initialize propeller.

        Args:
            x, y: Position in meters (fixed location)
            inertia: Rotational inertia in kg·m²
            rpm_nominal: Target RPM for governor
            k_aero: Aerodynamic torque coefficient
            governor_kp: Proportional gain for governor
            base_torque: Base engine torque at nominal conditions
        """
        # Position (stationary)
        self.x = x
        self.y = y

        # Physical properties
        self.inertia = inertia
        self.k_aero = k_aero

        # Governor parameters
        self.rpm_nominal = rpm_nominal
        self.omega_target = self.rpm_to_rad_s(rpm_nominal)
        self.governor_kp = governor_kp
        self.base_torque = base_torque

        # State variables
        self.omega = self.omega_target  # rad/s (start at target speed)
        self.rpm = rpm_nominal

        # Cached values for visualization
        self.rho_local = RHO_SEA_LEVEL  # Current local density
        self.q_aero = 0.0  # Current aerodynamic torque
        self.q_engine = base_torque  # Current engine torque
        self.q_net = 0.0  # Net torque
        self.alpha = 0.0  # Angular acceleration (rad/s²)

    @staticmethod
    def rpm_to_rad_s(rpm: float) -> float:
        """Convert RPM to rad/s."""
        return rpm * 2.0 * np.pi / 60.0

    @staticmethod
    def rad_s_to_rpm(omega: float) -> float:
        """Convert rad/s to RPM."""
        return omega * 60.0 / (2.0 * np.pi)

    def compute_aero_torque(self, rho_local: float, omega: float) -> float:
        """
        Compute aerodynamic torque based on local density and angular velocity.

        Simplified model: Q_aero = k * ρ * ω²
        This represents that thrust (and drag) scale with density and speed squared.

        Args:
            rho_local: Local atmospheric density (kg/m³)
            omega: Angular velocity (rad/s)

        Returns:
            Aerodynamic torque (Nm), always positive (opposes rotation)
        """
        return self.k_aero * rho_local * omega ** 2

    def compute_engine_torque(self, omega: float) -> float:
        """
        Compute engine torque from simple proportional governor.

        The governor increases torque when RPM is below target and
        decreases when above target.

        Q_engine = Q_base + K_P * (ω_target - ω)

        Args:
            omega: Current angular velocity (rad/s)

        Returns:
            Engine torque (Nm)
        """
        error = self.omega_target - omega
        q_engine = self.base_torque + self.governor_kp * error

        # Limit to physically reasonable range (can't go negative)
        q_engine = max(0.0, q_engine)

        return q_engine

    def update(self, dt: float, sim_time: float, density_field) -> None:
        """
        Update propeller state for one time step.

        Samples local density, computes torques, and integrates equation of motion.

        Args:
            dt: Time step (seconds)
            sim_time: Current simulation time (seconds)
            density_field: DensityField instance to sample from
        """
        # Sample local atmospheric density at propeller position
        self.rho_local = density_field.get_density(self.x, self.y, sim_time)

        # Compute torques
        self.q_aero = self.compute_aero_torque(self.rho_local, self.omega)
        self.q_engine = self.compute_engine_torque(self.omega)
        self.q_net = self.q_engine - self.q_aero

        # Compute angular acceleration: α = Q_net / I
        self.alpha = self.q_net / self.inertia

        # Integrate: ω(t+dt) = ω(t) + α * dt
        self.omega += self.alpha * dt

        # Prevent negative speeds (unrealistic)
        self.omega = max(0.0, self.omega)

        # Update RPM for convenience
        self.rpm = self.rad_s_to_rpm(self.omega)

    def get_state(self) -> dict:
        """
        Get current propeller state for logging/visualization.

        Returns:
            Dictionary with all state variables
        """
        return {
            'x': self.x,
            'y': self.y,
            'rpm': self.rpm,
            'omega': self.omega,
            'rho_local': self.rho_local,
            'q_aero': self.q_aero,
            'q_engine': self.q_engine,
            'q_net': self.q_net,
            'alpha': self.alpha,
            'rpm_error': self.rpm_nominal - self.rpm,
        }

    def __repr__(self):
        return (
            f"Propeller(x={self.x:.1f}m, y={self.y:.1f}m, "
            f"RPM={self.rpm:.1f}, ρ={self.rho_local:.4f} kg/m³)"
        )
