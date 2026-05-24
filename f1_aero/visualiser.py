import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.gridspec import GridSpec
from pathlib import Path
from typing import List, Optional

from .optimiser import AeroSweepResult


# Style constants
DARK_BG = "#0d0d0d"
PANEL_BG = "#141414"
GRID_COLOR = "#2a2a2a"
TEXT_COLOR = "#e8e8e8"
TEXT_MUTED = "#888888"
ACCENT_RED = "#e8003c"
ACCENT_BLUE = "#00a0e0"
ACCENT_AMBER = "#f5a623"
ACCENT_GREEN = "#39d353"

FONT_FAMILY = "monospace"


# Function to apply dark theme to any figure+(list of axes) that we parse

def _apply_base_style(fig, axes_list):
    fig.patch.set_facecolor(DARK_BG)
    for ax in axes_list:
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=TEXT_MUTED, labelsize=8)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        ax.title.set_color(TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_color(GRID_COLOR) # Makes figure borders (top,bottom,left,right) all dark-themed
        ax.grid(color=GRID_COLOR, linewidth=0.5, linestyle="--", alpha=0.6) # sets 60% transparency






# Figure 1: Plot Lap Time vs CL -----------------------------------------------------------------------------------------

def plot_lap_time_vs_CL(
    sweep: AeroSweepResult,
    save_path: Optional[Path] = None,
) -> plt.Figure:

    fig, ax = plt.subplots(figsize=(9, 5))
    _apply_base_style(fig, [ax])

    CL = sweep.CL_values
    T = sweep.lap_times
    opt = sweep.optimal

    # Main curve

    # controls the drawing order of elements. Higher zorder means drawn on top. 
    # We put the scatter markers (zorder=5) above the line (zorder=3) above the 
    # shaded region (zorder=1).
    ax.plot(CL, T, color=TEXT_COLOR, linewidth=1.8, zorder=3) 

    # Shade region within 0.1s of optimum
    mask = T <= opt.lap_time + 0.1
    ax.fill_between(CL, T, T.max() + 0.5, where=mask,
                    color=ACCENT_GREEN, alpha=0.07, zorder=1)

    # Optimum marker
    ax.axvline(opt.CL, color=ACCENT_GREEN, linewidth=1.2, linestyle="--", alpha=0.7)
    ax.scatter([opt.CL], [opt.lap_time], color=ACCENT_GREEN, s=80,
               zorder=5, edgecolors=DARK_BG, linewidths=1.5)
    ax.annotate(
        f" Optimum\n CL={opt.CL:.2f}, CD={opt.CD:.3f}\n T={opt.lap_time:.3f}s",
        xy=(opt.CL, opt.lap_time),
        xytext=(opt.CL + 0.15, opt.lap_time + 0.08),
        color=ACCENT_GREEN,
        fontsize=8,
        fontfamily=FONT_FAMILY,
        arrowprops=dict(arrowstyle="->", color=ACCENT_GREEN, lw=0.8),
    )

    # Low and high downforce markers
    ax.scatter([CL[0]], [T[0]], color=ACCENT_BLUE, s=50, zorder=5,
               edgecolors=DARK_BG, linewidths=1.2, label=f"Low DF  CL={CL[0]:.1f}")
    ax.scatter([CL[-1]], [T[-1]], color=ACCENT_AMBER, s=50, zorder=5,
               edgecolors=DARK_BG, linewidths=1.2, label=f"High DF  CL={CL[-1]:.1f}")

    ax.set_xlabel("Lift Coefficient  CL", fontfamily=FONT_FAMILY)
    ax.set_ylabel("Predicted Lap Time  [s]", fontfamily=FONT_FAMILY)
    ax.set_title(
        f"{sweep.circuit.name} {sweep.circuit.year} — Aero Optimisation",
        fontfamily=FONT_FAMILY, fontsize=11, pad=12,
    )
    ax.legend(facecolor=PANEL_BG, edgecolor=GRID_COLOR,
              labelcolor=TEXT_COLOR, fontsize=8)

    plt.tight_layout()

    # Can either save figure to disk or just return figure object
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    return fig







# Figure 2: Plot Circuit Map -----------------------------------------------------------------------------------------

def plot_circuit_map(
    sweep: AeroSweepResult,
    save_path: Optional[Path] = None,
) -> plt.Figure:

    circuit = sweep.circuit
    fig, ax = plt.subplots(figsize=(8, 8))
    _apply_base_style(fig, [ax])
    ax.set_aspect("equal")
    ax.axis("off")

    x, y = circuit.x, circuit.y
    kappa_abs = np.abs(circuit.curvature)

    # Normalize curvature to a 0-1 range 
    k_norm = (kappa_abs - kappa_abs.min()) / (kappa_abs.max() - kappa_abs.min() + 1e-9)

    cmap = mcolors.LinearSegmentedColormap.from_list(
        "aero", [ACCENT_BLUE, "#888888", ACCENT_RED], N=256
    )

    n = len(x)
    for i in range(n - 1):
        c = cmap(k_norm[i])
        ax.plot(x[i:i+2], y[i:i+2], color=c, linewidth=3.5, solid_capstyle="round")

    # Start/finish marker
    ax.scatter(x[0], y[0], color="white", s=120, zorder=10,
               edgecolors=DARK_BG, linewidths=2)
    ax.annotate("S/F", (x[0], y[0]), color="white", fontsize=7,
                fontfamily=FONT_FAMILY, ha="center", va="bottom",
                xytext=(0, 10), textcoords="offset points")

    # Colourbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02, shrink=0.6)
    cbar.ax.yaxis.set_tick_params(color=TEXT_MUTED, labelsize=7)
    cbar.set_ticks([0, 1])
    cbar.set_ticklabels(["Drag-sensitive", "Downforce-sensitive"],
                        color=TEXT_MUTED, fontfamily=FONT_FAMILY)
    cbar.outline.set_edgecolor(GRID_COLOR)

    ax.set_title(
        f"{circuit.name} {circuit.year} — Aero Sensitivity Map\n"
        f"Corner fraction: {circuit.corner_fraction:.1%}  |  "
        f"Optimal CL: {sweep.optimal.CL:.2f}",
        fontfamily=FONT_FAMILY, fontsize=10, color=TEXT_COLOR, pad=14,
    )

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    return fig

# Figure 3: Plot Speed Profiles -----------------------------------------------------------------------------------------

def plot_speed_profiles(
    sweep: AeroSweepResult,
    save_path: Optional[Path] = None,
) -> plt.Figure:

    fig, ax = plt.subplots(figsize=(12, 4))
    _apply_base_style(fig, [ax])

    low = sweep.results[0]
    opt = sweep.optimal
    high = sweep.results[-1]
    s_km = opt.s / 1000


    ax.plot(s_km, low.v * 3.6, color=ACCENT_BLUE, linewidth=1.2,
            alpha=0.85, label=f"Low DF  CL={low.CL:.2f}  T={low.lap_time:.2f}s") # we multiply by 3.6 to convrert m/s -> km/h for easier intuition
    ax.plot(s_km, opt.v * 3.6, color=ACCENT_GREEN, linewidth=1.8,
            alpha=0.95, label=f"Optimal  CL={opt.CL:.2f}  T={opt.lap_time:.2f}s")
    ax.plot(s_km, high.v * 3.6, color=ACCENT_AMBER, linewidth=1.2,
            alpha=0.85, label=f"High DF  CL={high.CL:.2f}  T={high.lap_time:.2f}s")

    # Shade corner regions
    circuit = sweep.circuit
    in_corner = circuit.corner_mask

    # Convert the boolean corner mask into integers (0 or 1);
    # We consider a "change" whenever the value goes from 0->1 or 1->0
    # Each "change" is a boundary b/w corner and straight
    changes = np.where(np.diff(in_corner.astype(int)) != 0)[0] + 1 

    # Prepend 0 and Append last index to get a list of segment boundaries
    boundaries = np.concatenate([[0], changes, [len(in_corner)]])


    for i in range(len(boundaries) - 1):
        if in_corner[boundaries[i]]:
            ax.axvspan(
                circuit.s[boundaries[i]] / 1000, # converts m -> km for easier visual interpretation
                circuit.s[min(boundaries[i+1], len(circuit.s)-1)] / 1000,
                color=ACCENT_RED, alpha=0.05, linewidth=0,
            )

    ax.set_xlabel("Distance  [km]", fontfamily=FONT_FAMILY)
    ax.set_ylabel("Speed  [km/h]", fontfamily=FONT_FAMILY)
    ax.set_title(
        f"{sweep.circuit.name} — Speed Profiles by Aero Configuration",
        fontfamily=FONT_FAMILY, fontsize=10,
    )
    ax.legend(facecolor=PANEL_BG, edgecolor=GRID_COLOR,
              labelcolor=TEXT_COLOR, fontsize=8)
    ax.set_xlim(0, s_km[-1])

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    return fig

# Figure 4: Plot Circuit Speed Heatmap -----------------------------------------------------------------------------------------


def plot_speed_heatmap(
    sweep: AeroSweepResult,
    save_path: Optional[Path] = None,
) -> plt.Figure:

    circuit = sweep.circuit
    opt = sweep.optimal

    fig, ax = plt.subplots(figsize=(8, 8))
    _apply_base_style(fig, [ax])
    ax.set_aspect("equal")
    ax.axis("off")

    x, y = circuit.x, circuit.y
    v_kmh = opt.v * 3.6

    # Normalise speed for colouring
    v_min, v_max = v_kmh.min(), v_kmh.max()
    v_norm = (v_kmh - v_min) / (v_max - v_min + 1e-9)

    # Colour map: dark blue (slow) through cyan to white (fast)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "speed", ["#0d0d8f", "#00a0e0", "#39d353", "#f5a623", "#e8003c"], N=256
    )

    n = len(x)
    for i in range(n - 1):
        c = cmap(v_norm[i])
        ax.plot(x[i:i+2], y[i:i+2], color=c, linewidth=3.5, solid_capstyle="round")

    # Start/finish marker
    ax.scatter(x[0], y[0], color="white", s=120, zorder=10,
               edgecolors=DARK_BG, linewidths=2)
    ax.annotate("S/F", (x[0], y[0]), color="white", fontsize=7,
                fontfamily=FONT_FAMILY, ha="center", va="bottom",
                xytext=(0, 10), textcoords="offset points")

    # Colourbar showing actual speed values
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(v_min, v_max))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02, shrink=0.6)
    cbar.ax.yaxis.set_tick_params(color=TEXT_COLOR, labelsize=9)
    cbar.set_label("Speed  [km/h]", color=TEXT_COLOR,
                   fontfamily=FONT_FAMILY, fontsize=8)
    cbar.outline.set_edgecolor(GRID_COLOR)

    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT_COLOR, 
         fontfamily=FONT_FAMILY, fontsize=8)

    ax.set_title(
        f"{circuit.name} {circuit.year} — Speed Heatmap\n"
        f"Optimal configuration: CL={opt.CL:.2f}  CD={opt.CD:.3f}",
        fontfamily=FONT_FAMILY, fontsize=10, color=TEXT_COLOR, pad=14,
    )

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    return fig

# Plot Summary Dashboard -----------------------------------------------------------------------------------------


def plot_summary_dashboard(
    sweep: AeroSweepResult,
    save_path: Optional[Path] = None,
) -> plt.Figure:

    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor(DARK_BG)
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.28)

    ax_map = fig.add_subplot(gs[0, 0])
    ax_lt = fig.add_subplot(gs[0, 1])
    ax_spd = fig.add_subplot(gs[1, :])

    _apply_base_style(fig, [ax_map, ax_lt, ax_spd])

    # -- Circuit map --
    circuit = sweep.circuit
    x, y = circuit.x, circuit.y
    kappa_abs = np.abs(circuit.curvature)
    k_norm = (kappa_abs - kappa_abs.min()) / (kappa_abs.max() - kappa_abs.min() + 1e-9)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "aero", [ACCENT_BLUE, "#888888", ACCENT_RED], N=256
    )
    n = len(x)
    for i in range(n - 1):
        ax_map.plot(x[i:i+2], y[i:i+2], color=cmap(k_norm[i]),
                    linewidth=2.5, solid_capstyle="round")
    ax_map.scatter(x[0], y[0], color="white", s=80, zorder=10,
                   edgecolors=DARK_BG, linewidths=1.5)
    ax_map.set_aspect("equal")
    ax_map.axis("off")
    ax_map.set_title(
        f"Aero Sensitivity Map\nCorner fraction: {circuit.corner_fraction:.1%}",
        fontfamily=FONT_FAMILY, fontsize=9, color=TEXT_COLOR,
    )

    # -- Lap time vs CL --
    CL, T = sweep.CL_values, sweep.lap_times
    opt = sweep.optimal
    ax_lt.plot(CL, T, color=TEXT_COLOR, linewidth=1.6, zorder=3)
    ax_lt.scatter([opt.CL], [opt.lap_time], color=ACCENT_GREEN, s=70,
                  zorder=5, edgecolors=DARK_BG, linewidths=1.5)
    ax_lt.axvline(opt.CL, color=ACCENT_GREEN, linewidth=1.0,
                  linestyle="--", alpha=0.6)
    ax_lt.set_xlabel("CL", fontfamily=FONT_FAMILY, fontsize=9)
    ax_lt.set_ylabel("Lap Time  [s]", fontfamily=FONT_FAMILY, fontsize=9)
    ax_lt.set_title(
        f"Lap Time vs CL\nOptimum: CL={opt.CL:.2f}  T={opt.lap_time:.3f}s",
        fontfamily=FONT_FAMILY, fontsize=9, color=TEXT_COLOR,
    )

    # -- Speed profiles --
    low, high = sweep.results[0], sweep.results[-1]
    s_km = opt.s / 1000
    ax_spd.plot(s_km, low.v * 3.6, color=ACCENT_BLUE, linewidth=1.0,
                alpha=0.8, label=f"Low DF CL={low.CL:.2f}")
    ax_spd.plot(s_km, opt.v * 3.6, color=ACCENT_GREEN, linewidth=1.6,
                alpha=0.95, label=f"Optimal CL={opt.CL:.2f}")
    ax_spd.plot(s_km, high.v * 3.6, color=ACCENT_AMBER, linewidth=1.0,
                alpha=0.8, label=f"High DF CL={high.CL:.2f}")

    in_corner = circuit.corner_mask
    changes = np.where(np.diff(in_corner.astype(int)) != 0)[0] + 1
    boundaries = np.concatenate([[0], changes, [len(in_corner)]])
    for i in range(len(boundaries) - 1):
        if in_corner[boundaries[i]]:
            ax_spd.axvspan(
                circuit.s[boundaries[i]] / 1000,
                circuit.s[min(boundaries[i+1], len(circuit.s)-1)] / 1000,
                color=ACCENT_RED, alpha=0.05, linewidth=0,
            )

    ax_spd.set_xlabel("Distance  [km]", fontfamily=FONT_FAMILY, fontsize=9)
    ax_spd.set_ylabel("Speed  [km/h]", fontfamily=FONT_FAMILY, fontsize=9)
    ax_spd.set_title("Speed Profiles by Aero Configuration",
                     fontfamily=FONT_FAMILY, fontsize=9, color=TEXT_COLOR)
    ax_spd.legend(facecolor=PANEL_BG, edgecolor=GRID_COLOR,
                  labelcolor=TEXT_COLOR, fontsize=8)
    ax_spd.set_xlim(0, s_km[-1])

    fig.suptitle(
        f"F1 Aero Optimiser  ·  {circuit.name} {circuit.year}",
        fontfamily=FONT_FAMILY, fontsize=13, color=TEXT_COLOR, y=0.98,
    )

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    return fig





if __name__ == "__main__":
    import fastf1
    import matplotlib
    matplotlib.use("Agg")
    from f1_aero.circuit import load_circuit
    from f1_aero.vehicle import VehicleParams
    from f1_aero.optimiser import run_aero_sweep

    fastf1.Cache.enable_cache("cache/")

    circuit = load_circuit("Italian", year=2023)
    params = VehicleParams.from_yaml("config/car_params.yaml")
    sweep = run_aero_sweep(circuit, params)

    plot_summary_dashboard(sweep, save_path=Path("outputs/italian_dashboard.png"))
    plot_lap_time_vs_CL(sweep, save_path=Path("outputs/italian_lap_time.png"))
    plot_circuit_map(sweep, save_path=Path("outputs/italian_circuit_map.png"))
    plot_speed_profiles(sweep, save_path=Path("outputs/italian_speed_profiles.png"))
    plot_speed_heatmap(sweep,save_path=Path("outputs/italian_speed_heatmap.png"))

    print("Figures saved to outputs/")