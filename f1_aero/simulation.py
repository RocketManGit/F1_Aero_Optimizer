import numpy as np
from dataclasses import dataclass
from .circuit import CircuitProfile
from .vehicle import VehicleModel


@dataclass
class LapResult:
    lap_time: float
    v: np.ndarray
    s: np.ndarray
    CL: float
    CD: float
    time_in_corners: float
    time_on_straights: float

    # decorator allows us to call v_max() as just v_max, i.e without () brackets
    @property
    def v_max(self) -> float:
        return float(np.max(self.v))

    @property
    def v_min(self) -> float:
        return float(np.min(self.v))
    


def simulate_lap(circuit: CircuitProfile, vehicle: VehicleModel) -> LapResult:

    s = circuit.s # Arc length at each point along track
    kappa = circuit.curvature # Curvature at each point along track 
    n = len(s)

    # Arc-length step sizes
    ds = np.diff(s, append=s[-1] + (s[1] - s[0]))
    ds = np.clip(ds, 1e-3, None) # If the diff b/w 2 lengths is 0, we clip to 0.001

    # Elevation gradient at each point
    gradient = np.gradient(circuit.elevation, s) # Found by differentiating height with arc length at each point along track
    gradient = np.clip(gradient, -0.15, 0.15) # Clip gradients to handle noisy measurements

    # --- Pass 1: Corner speed limit ---
    with np.errstate(divide="ignore"):
        radius = np.where(np.abs(kappa) > 1e-6, 1.0 / np.abs(kappa), 1e6) # Since radius is the inverse of curvature but it is capped at 1 mil if curvature is 0

    v_corner = vehicle.max_cornering_speed(radius, gradient)

    # v_corner is the max possible speed at every point on the track (due to local curvature)
    # The car CANNOT GO PHYSICALLY FASTER THAN THIS!
    # However, we also need to consider if the car can brake/accelerate fast enough to achieve given speeds on the track
    # To make this possible, the max speed at each point will be altered until the above is satisfied at all points along the track






    # --- Pass 2: Backward pass (braking) ---

    # We traverse the circuit in reverse to see if the car can brake in time to achieve certain
    # speeds when entering corners

    v_back = v_corner.copy() # Creates a copy of the array of max cornering speeds
    for i in range(n - 1, -1, -1):
        j = (i + 1) % n # By using moduus, we also consider a special case when i is at the end and then j can be at the start (wraps around since closed circuit)
        step = ds[i] # Arc length difference at that point along track

        # Calculates max braking deceleration considering velocity to be achieved at next point
        a_brake = vehicle.max_braking_deceleration(
            np.array([v_back[j]]), gradient[i]
        )[0]

        # Calculate max velocity based on max deceleration from kinematics eqn: v2=u2+2as
        v_achievable = np.sqrt(max(v_back[j]**2 + 2.0 * a_brake * step, 0.0))

        # Adjusts the new max speeds along the circuit
        v_back[i] = min(v_back[i], v_achievable)

        # Now the circuit goes backward 1 step and the next point has already been adjusted to min(v_back,v_achievable)




    # --- Pass 3: Forward pass (acceleration) ---

    # We traverse the circuit forwards to see if the car can accelerate in time to achieve certain
    # speeds when exiting corners

    v_fwd = v_back.copy() # creates a copy of the array of max cornering or deceleration speeds (as found above)

    for _ in range(2):
        for i in range(n):
            j = (i - 1) % n
            step = ds[j]

            # This acceleration is either limited by tyre grip or engine power
            a_trac = vehicle.max_traction_acceleration(
                np.array([v_fwd[j]]), gradient[i]
            )[0]

            # Calculate max velocity based on max deceleration from kinematics eqn: v2=u2+2as
            v_achievable = np.sqrt(max(v_fwd[j]**2 + 2.0 * a_trac * step, 0.0))

            # Adjusts the new max speeds along the circuit
            v_fwd[i] = min(v_fwd[i], v_achievable)

            # Now the circuit goes forward 1 step and the prev point has already been adjusted to min(v_fwd,v_achievable)




    # The array of speed that remains represents the maximum possible speed that can be achieved
    # at each point along the track considering max cornering speed, having to decelerate into corners
    # and accelerate out of corners



    # --- Step 4: Integrate lap time ---
    v = np.clip(v_fwd, 1.0, 120.0) # We put lower bound as 1 m/s to prevent Division By Zero

    dt = ds / v # Calculates duration in each window considering max speeds

    lap_time = float(np.sum(dt)) # Sums up all durations to find total lap time

    time_in_corners = float(np.sum(dt[circuit.corner_mask])) # Adds up durations associated portions with the corner mask
    time_on_straights = float(np.sum(dt[circuit.straight_mask])) # Adds up durations associated portions without the corner mask

    return LapResult(
        lap_time=lap_time,
        v=v,
        s=s,
        CL=vehicle.CL,
        CD=vehicle.CD,
        time_in_corners=time_in_corners,
        time_on_straights=time_on_straights,
    )


if __name__ == "__main__":
    import fastf1
    from f1_aero.circuit import load_circuit
    from f1_aero.vehicle import VehicleParams, VehicleModel

    fastf1.Cache.enable_cache("cache/")

    circuit = load_circuit("Italian", year=2023)
    params = VehicleParams.from_yaml("config/car_params.yaml")
    car = VehicleModel(params, CL=3.0)

    result = simulate_lap(circuit, car)
    print(f"Lap time: {result.lap_time:.3f} s")
    print(f"Max speed: {result.v_max*3.6:.1f} km/h")
    print(f"Min speed: {result.v_min*3.6:.1f} km/h")
    print(f"Time in corners: {result.time_in_corners:.1f} s")
    print(f"Time on straights: {result.time_on_straights:.1f} s")