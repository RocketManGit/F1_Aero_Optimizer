import numpy as np
from dataclasses import dataclass
from pathlib import Path
import yaml

# VehicleParams class solely stores all vehicle parameters
@dataclass
class VehicleParams:
    mass_kg: float
    frontal_area_m2: float
    peak_power_kw: float
    drivetrain_efficiency: float
    tyre_friction_coeff: float
    friction_ellipse_ratio: float
    CD0: float
    k: float
    CL_min: float
    CL_max: float
    CL_steps: int
    rolling_resistance_coeff: float
    air_density_kg_m3: float

    # Uses classmethod to automatically parse data from the YAML file containing key:value 
    # pairs of vehicle parameters and their corresponding values
    @classmethod
    def from_yaml(cls, path):
        with open(path, "r") as f:
            d = yaml.safe_load(f)
        return cls(**{field: d[field] for field in cls.__dataclass_fields__})
    

# Class that holds information about vehicle params and CL
# CL is considered separately because it will be an optimization variable over whose values
# we willl sweep over
class VehicleModel:
    def __init__(self, params: VehicleParams, CL: float):
        self.p = params
        self.CL = CL
        self.CD = params.CD0 + params.k * CL**2 # Computes CD using drag polar

        # Calculates some useful terms that will be used by later physics equations
        self._half_rho_A = 0.5 * params.air_density_kg_m3 * params.frontal_area_m2
        self._peak_power_W = params.peak_power_kw * 1000 * params.drivetrain_efficiency
        self._g = 9.81


    # 4 Physics Forces Equations

    def aero_downforce(self, v: np.ndarray) -> np.ndarray:
            return self._half_rho_A * self.CL * v**2 # Uses standard lift equation using CL

    def aero_drag(self, v: np.ndarray) -> np.ndarray:
        return self._half_rho_A * self.CD * v**2 # Uses standard drag equation using CD

    def rolling_resistance(self, v: np.ndarray) -> np.ndarray:
        return self.p.rolling_resistance_coeff * self.p.mass_kg * self._g * np.ones_like(v) # Finds rolling resistance at each data point (same shape as v array)

    def normal_force(self, v: np.ndarray, gradient: float = 0.0) -> np.ndarray:
        weight_normal = self.p.mass_kg * self._g * np.cos(gradient) # Weight of car adjusted with road's gradient
        return weight_normal + self.aero_downforce(v) # Added to the aero down force
    

    # 3 Speed Limit Equations


    # Solves for v from the equation: μ_lat × (mg·cos θ + ½ρA·CL·v²) = mv²/R
    # More downforce = More grip = More cornering speed
    def max_cornering_speed(self, radius: np.ndarray, gradient: float = 0.0) -> np.ndarray:
        mu_lat = self.p.tyre_friction_coeff * self.p.friction_ellipse_ratio # Lateral tyre friction coeff based on ellipse ratio
        m = self.p.mass_kg

        weight_lat = m * self._g * np.cos(gradient)
        denom = m / radius - mu_lat * self._half_rho_A * self.CL

        # Returns the calculated max cornering speed BUT if denom=0, returns a very large number (1e6)
        # The reason: Based on the equation, if denom is negative becuase downforce is so large, then
        # tyre grip is never the limiting factor and max cornering speed can be infinity

        with np.errstate(invalid="ignore", divide="ignore"):
            v2 = np.where(
                denom > 0,
                mu_lat * weight_lat / denom,
                1e6
            )

        return np.sqrt(np.clip(v2, 0, 120**2))
    

    # At low speeds the tyres spin before the engine maxes out (grip-limited). 
    # At high speeds the engine maxes out before the tyres spin (power-limited). 
    # We compute both limits and take the minimum — whichever constraint is active at that 
    # speed.
    def max_traction_acceleration(self, v: np.ndarray, gradient: float = 0.0) -> np.ndarray:
        m = self.p.mass_kg
        mu_lon = self.p.tyre_friction_coeff
        N = self.normal_force(v, gradient) # Finding max normal force for given velocity and slope

        max_lon_force=mu_lon*N # Max longitudinal force that the tyres can generate
        max_lon_acc=max_lon_force/m # Max longitudinal acceleration of tyres by F=ma
        a_grip = max_lon_acc - self._g * np.sin(gradient) # If car is going uphill, we need to account for gravity

        drag = self.aero_drag(v) + self.rolling_resistance(v) # Total resistive force to engine

        # Max engine force is based on peak power and velocity (F=P/v); But if car is almost at standstill
        # at low velocity, then we ignore the velocity term to avoid dividing by 0
        with np.errstate(divide="ignore", invalid="ignore"):
            F_engine = np.where(v > 1.0, self._peak_power_W / v, self._peak_power_W)

        # Max acceleration limited by engine power also considering road slope    
        a_power = (F_engine - drag) / m - self._g * np.sin(gradient)

        return np.minimum(a_grip, a_power)

    def max_braking_deceleration(self, v: np.ndarray, gradient: float = 0.0) -> np.ndarray:
        m = self.p.mass_kg
        mu_lon = self.p.tyre_friction_coeff
        N = self.normal_force(v, gradient) # Finding max normal force for given velocity and slope

        drag = self.aero_drag(v) + self.rolling_resistance(v) # Total resistive force to engine

        # Unlike acceleration, there are 3 things that contribute to braking deceleration:
        # tyre braking force, (aero drag + rolling resistance) and gravity if car is going dowhill
        a_brake = mu_lon * N / m + drag / m + self._g * np.sin(gradient)

        return a_brake
    


if __name__ == "__main__":
    params = VehicleParams.from_yaml("config/car_params.yaml")
    car = VehicleModel(params, CL=3.0)

    import numpy as np
    print(f"CD for CL=3.0: {car.CD:.3f}")
    print(f"Downforce at 100 m/s: {car.aero_downforce(np.array([100.0]))[0]:.0f} N")
    print(f"Drag at 100 m/s:      {car.aero_drag(np.array([100.0]))[0]:.0f} N")
    print(f"Max corner speed at R=200m: {car.max_cornering_speed(np.array([200.0]))[0]*3.6:.1f} km/h")