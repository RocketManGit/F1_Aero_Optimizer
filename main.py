# argparse helps define what arguments program will accept and 
# automatically generate help text (rather than hardcoding parameter values)
import argparse


import sys
from pathlib import Path

import fastf1
import matplotlib

# Set matplotlib to a non-interactive backend that only saves figs to disk 
# rather than opening figure window
matplotlib.use("Agg")

from f1_aero.circuit import load_circuit
from f1_aero.vehicle import VehicleParams
from f1_aero.optimiser import run_aero_sweep
from f1_aero.visualiser import (
    plot_summary_dashboard,
    plot_lap_time_vs_CL,
    plot_circuit_map,
    plot_speed_profiles,
    plot_speed_heatmap,
)



def main():
    parser = argparse.ArgumentParser(
        description="F1 Aerodynamic Configuration Optimiser",
    )
    parser.add_argument(
        "--gp", nargs="+", required=True,
        help="Grand Prix name(s), e.g. --gp Italian Monaco British",
    )
    parser.add_argument(
        "--year", type=int, default=2023,
        help="Season year (default: 2023)",
    )
    parser.add_argument(
        "--params", default="config/car_params.yaml",
        help="Path to car parameters YAML (default: config/car_params.yaml)",
    )
    parser.add_argument(
        "--output", default="outputs/",
        help="Directory to save figures (default: outputs/)",
    )
    parser.add_argument(
        "--cache", default="cache/",
        help="FastF1 cache directory (default: cache/)",
    )
    args = parser.parse_args()

    # Set up directories
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Configure FastF1 cache
    fastf1.Cache.enable_cache(str(cache_dir))

    # Load car parameters
    params_path = Path(args.params)
    if not params_path.exists():
        print(f"[ERROR] Car params file not found: {params_path}")
        sys.exit(1)
    print(f"\nLoading car parameters from: {params_path}")
    params = VehicleParams.from_yaml(params_path)

    # Run analysis for each circuit (if multiple circuits are defined in input)
    sweeps = []
    for gp in args.gp:
        print(f"\n{'='*60}")
        print(f"  Processing: {gp} GP {args.year}")
        print(f"{'='*60}")

        try:
            circuit = load_circuit(gp, year=args.year)
        except Exception as e:
            print(f"[ERROR] Could not load circuit data for '{gp}': {e}") # Prints error if can't find Grand Prix name from FastF1
            continue

        sweep = run_aero_sweep(circuit, params, verbose=True)
        sweeps.append(sweep)

        # Save figures
        gp_slug = gp.lower().replace(" ", "_")
        print(f"\n  Saving figures to {output_dir}/")

        plot_summary_dashboard(
            sweep,
            save_path=output_dir / f"{gp_slug}_{args.year}_dashboard.png",
        )
        plot_lap_time_vs_CL(
            sweep,
            save_path=output_dir / f"{gp_slug}_{args.year}_lap_time_vs_CL.png",
        )
        plot_circuit_map(
            sweep,
            save_path=output_dir / f"{gp_slug}_{args.year}_circuit_map.png",
        )
        plot_speed_profiles(
            sweep,
            save_path=output_dir / f"{gp_slug}_{args.year}_speed_profiles.png",
        )
        plot_speed_heatmap(
            sweep,
            save_path=output_dir / f"{gp_slug}_{args.year}_speed_heatmap.png",
        )

        import matplotlib.pyplot as plt
        plt.close("all") # Close all figures

        print(f"    ✓ {gp_slug}_{args.year}_dashboard.png")
        print(f"    ✓ {gp_slug}_{args.year}_lap_time_vs_CL.png")
        print(f"    ✓ {gp_slug}_{args.year}_circuit_map.png")
        print(f"    ✓ {gp_slug}_{args.year}_speed_profiles.png")
        print(f"    ✓ {gp_slug}_{args.year}_speed_heatmap.png")

    print(f"\n{'='*60}")
    print(f"  Done. All outputs saved to: {output_dir.resolve()}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()


