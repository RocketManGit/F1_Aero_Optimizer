import numpy as np
from dataclasses import dataclass, field
from typing import List
from .circuit import CircuitProfile
from .vehicle import VehicleModel, VehicleParams
from .simulation import LapResult, simulate_lap


@dataclass
class AeroSweepResult:
    results: List[LapResult] # imported from 'typing' module, this explicitly type casts the variable as a list of 'LapResult' objects
    CL_values: np.ndarray
    CD_values: np.ndarray
    lap_times: np.ndarray
    optimal: LapResult # stores the optimal as a 'LapResult' object

    # represents how many milliseconds do you lose per lap if, 
    # at the optimal wing setting, you add 10 counts of drag (i.e ΔCD = 0.010)
    # A high sensitivity means the circuit is very punishing of drag (like Monza). 
    # A low sensitivity means the circuit is more forgiving (like Monaco where top speed matters less).
    sensitivity_ms_per_10_counts: float 

    # represents lap time (at max CL) - lap time (at min CL)
    # Also represents how many seconds you lose if running the highest downforce setup minus lowest downforce setup
    # Gives a sense of the aero sensitivity of the circuit (how much does wing setting impact lap time)
    delta_low_to_high: float


    circuit: CircuitProfile # stores the circuit as a 'CircuitProfile' object




def run_aero_sweep(
    circuit: CircuitProfile,
    params: VehicleParams,
    verbose: bool = True,
) -> AeroSweepResult:


    CL_values = np.linspace(params.CL_min, params.CL_max, params.CL_steps) # Range of CL values to sweeo through
    results = [] # List of "LapResult" objects

    if verbose:
        print(f"\nRunning aero sweep: {len(CL_values)} configurations...")

    for i, CL in enumerate(CL_values):
        vehicle = VehicleModel(params, CL) # Builds vehicle object with that CL value
        result = simulate_lap(circuit, vehicle) # Simulates lap with that CL
        results.append(result) # Appends 'LapResult' object

        # Print Lap Results at intervals
        if verbose and (i % 5 == 0 or i == len(CL_values) - 1):
            print(f"  CL={CL:.2f}  CD={result.CD:.3f}  Lap time={result.lap_time:.3f}s")


    CD_values = np.array([r.CD for r in results])
    lap_times = np.array([r.lap_time for r in results])

    # Find optimal configuration
    opt_idx = int(np.argmin(lap_times))
    optimal = results[opt_idx]

    # Sensitivity: d(lap_time)/d(CD) at optimum, converted to ms per 10 counts (using central difference theorem to calculate derivative at optimal CL point)
    if 0 < opt_idx < len(results) - 1:
        dT_dCD = (
            (lap_times[opt_idx + 1] - lap_times[opt_idx - 1])
            / (CD_values[opt_idx + 1] - CD_values[opt_idx - 1])
        )

    # Special Case: If the optimal point is at the start/end, we don't have 2 points on either side for central difference theorem
    else:
        dT_dCD = np.gradient(lap_times, CD_values)[opt_idx]

    sensitivity_ms_per_10_counts = dT_dCD * 0.001 * 1000 # since 10 counts in CD units and converting from seconds to milliseconds



    
    delta_low_to_high = float(lap_times[-1] - lap_times[0])




    if verbose:
        print(f"\nOptimal CL: {optimal.CL:.2f}  CD={optimal.CD:.3f}")
        print(f"Optimal lap time: {optimal.lap_time:.3f}s")
        print(f"Sensitivity: {sensitivity_ms_per_10_counts:+.1f} ms per 10 drag counts")
        print(f"Low to high downforce delta: {delta_low_to_high:+.3f}s")

    return AeroSweepResult(
        results=results,
        CL_values=CL_values,
        CD_values=CD_values,
        lap_times=lap_times,
        optimal=optimal,
        sensitivity_ms_per_10_counts=float(sensitivity_ms_per_10_counts),
        delta_low_to_high=delta_low_to_high,
        circuit=circuit,
)


if __name__ == "__main__":
    import fastf1
    from f1_aero.circuit import load_circuit

    fastf1.Cache.enable_cache("cache/")

    circuit = load_circuit("Italian", year=2023)
    params = VehicleParams.from_yaml("config/car_params.yaml")
    sweep = run_aero_sweep(circuit, params)