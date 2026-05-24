import numpy as np
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d
from dataclasses import dataclass
import fastf1
import warnings

warnings.filterwarnings("ignore")

# Using a decorator, automatically creates CircuitProfile class
# to store all the relevant info about a circuit
@dataclass
class CircuitProfile:
    s: np.ndarray          # Arc-length along track [m]
    x: np.ndarray          # Smoothed x coordinates [m]
    y: np.ndarray          # Smoothed y coordinates [m]
    elevation: np.ndarray  # Altitude [m]
    curvature: np.ndarray  # Local curvature κ(s) [1/m]
    corner_mask: np.ndarray   # True where cornering
    straight_mask: np.ndarray # True where straight
    total_length: float
    corner_fraction: float
    name: str
    year: int

# Function to find distance from start at each discretized point along circuit
# using straight-line distance formula

def _arc_length(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Cumulative arc-length along a polyline."""

    dx = np.diff(x, prepend=x[0]) # Returns x[i]-x[i-1] as np.array()
    dy = np.diff(y, prepend=y[0]) # Returns x[i]-x[i-1] as np.array()
    ds = np.sqrt(dx**2 + dy**2) # Returns straight line distance b/w each point using X,Y coords
    ds[0] = 0.0
    return np.cumsum(ds)


# Function to comput curvature at each point along circuit profile

def _curvature(x: np.ndarray, y: np.ndarray, s: np.ndarray) -> np.ndarray:
    """Signed curvature of a planar curve parameterised by arc length s."""
    xp = np.gradient(x, s) # Computes dx/ds
    yp = np.gradient(y, s) # Computes dy/ds

    xpp = np.gradient(xp, s) # Computes d2x/ds2
    ypp = np.gradient(yp, s) # Computes d2y/ds2

    # 2D Curvature Equation using x and y differentials
    numerator = xp * ypp - yp * xpp
    denominator = (xp**2 + yp**2) ** (3/2)

    with np.errstate(invalid="ignore", divide="ignore"):
        kappa = np.where(np.abs(denominator) > 1e-10, numerator / denominator, 0.0)

    return kappa


# Function to load circuit (points to CircuitProfile class to signal that the return type 
# will be an object instance of that class) and fastest session's telemetry readings 
# Does resampling to make it uniformly spaced
# Does Savitzky-Golay filtering to handle noise

def load_circuit(
    grand_prix: str,
    year: int = 2023,
    curvature_threshold: float = 0.004,
    smoothing_window: int = 51,
    resample_points: int = 2000,
) -> CircuitProfile:

    print(f"Loading {year} {grand_prix} GP...")
    session = fastf1.get_session(year, grand_prix, "Q")
    session.load(telemetry=True, weather=False, messages=False)

    fastest = session.laps.pick_fastest()
    tel = fastest.get_telemetry()

    # Extract coordinates
    x_raw = tel["X"].values.astype(float)
    y_raw = tel["Y"].values.astype(float)
    z_raw = tel["Z"].values.astype(float)

    # Convert coordinates from decimetres -> metres
    x_raw = tel["X"].values.astype(float) / 10
    y_raw = tel["Y"].values.astype(float) / 10
    z_raw = tel["Z"].values.astype(float) / 10

    # Remove NaNs
    valid = ~(np.isnan(x_raw) | np.isnan(y_raw) | np.isnan(z_raw))
    x_raw, y_raw, z_raw = x_raw[valid], y_raw[valid], z_raw[valid]

    # Resample to uniform arc-length spacing

    # Explanation: 
    # Car speed is faster along straights than on bends which means the recorded
    # telemetry coords will be further apart on straights than on bends (distance-wise);
    # Therfore, we do resampling through cubic interpolation to keep it uniformly spaced
    s_raw = _arc_length(x_raw, y_raw)
    s_uniform = np.linspace(0, s_raw[-1], resample_points)
    x = interp1d(s_raw, x_raw, kind="cubic")(s_uniform)
    y = interp1d(s_raw, y_raw, kind="cubic")(s_uniform)
    z = interp1d(s_raw, z_raw, kind="cubic")(s_uniform)

    # Smooth with Savitzky-Golay filter

    # Explanation: 
    # GPS telemetry might still be noisy; This gets amplified when doing double differentiation
    # when computing curvature; so we use savgol filter to fit a cubic polynomial
    # to the noisy data; The mode "wrap" tells it to consider the data as circular which is
    # true, because X,Y,Z at start of lap is equal to X,Y,Z at end of lap
    x = savgol_filter(x, smoothing_window, polyorder=3, mode="wrap")
    y = savgol_filter(y, smoothing_window, polyorder=3, mode="wrap")
    z = savgol_filter(z, smoothing_window, polyorder=3, mode="wrap")

    # Recompute arc length on smoothed coordinates
    s = _arc_length(x, y)

    # Compute and smooth curvature
    kappa = _curvature(x, y, s)
    kappa = savgol_filter(kappa, 21, polyorder=2, mode="wrap")

    # Classify corner_mask array based on a pre-defined kappa threshold

    # Explanation:
    # If corner_mask=True, then that point belongs to a corner
    corner_mask = np.abs(kappa) > curvature_threshold

    # Create straight_mask
    straight_mask = ~corner_mask

    # Corner fraction by arc length
    ds = np.diff(s, append=s[-1] + (s[1] - s[0])) # Computes the length of segments between each point
    corner_fraction = np.sum(ds[corner_mask]) / s[-1] # Sums up indiv. lengths and finds fraction of total circuit that belongs to corners

    print(f"Circuit length: {s[-1]:.0f} m | Corner fraction: {corner_fraction:.1%}")

    return CircuitProfile(
        s=s, x=x, y=y, elevation=z,
        curvature=kappa,
        corner_mask=corner_mask,
        straight_mask=straight_mask,
        total_length=float(s[-1]),
        corner_fraction=float(corner_fraction),
        name=f"{grand_prix} Grand Prix",
        year=year,
    )

# Test out code
if __name__ == "__main__":
    fastf1.Cache.enable_cache("cache/")
    circuit = load_circuit("Italian", year=2023)
    print(f"Curvature range: {circuit.curvature.min():.4f} to {circuit.curvature.max():.4f}")
    print(f"Corner fraction: {circuit.corner_fraction:.1%}")


