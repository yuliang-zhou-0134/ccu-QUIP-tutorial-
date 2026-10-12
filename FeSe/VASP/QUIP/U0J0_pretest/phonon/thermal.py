#!/usr/bin/env python3
"""Reproduce harmonic thermodynamics from saved Phonopy force constants."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import phonopy
from phonopy import load


ROOT = Path(__file__).resolve().parents[1]
VASP_TO_THZ = 15.633302
THZ_TO_MEV = 4.135667696
GAS_CONSTANT = 8.31446261815324


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT
        / "phonon"
        / "output_reproduction_4x4"
        / "csc_ver_reproduced_4x4.yaml",
    )
    parser.add_argument(
        "--historical-yaml", type=Path, default=ROOT / "phonon" / "csc_ver.yaml"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "phonon" / "output_thermal_reproduction",
    )
    parser.add_argument("--mesh", type=int, nargs=3, default=(30, 30, 30))
    parser.add_argument("--t-min", type=float, default=0.0)
    parser.add_argument("--t-max", type=float, default=1000.0)
    parser.add_argument("--t-step", type=float, default=10.0)
    return parser.parse_args()


def calculate(path: Path, mesh: tuple[int, int, int], args: argparse.Namespace):
    ph = load(path.resolve(), produce_fc=True)
    if ph.force_constants is None or not np.isfinite(ph.force_constants).all():
        raise SystemExit(f"error: missing or non-finite force constants in {path}")
    ph.unit_conversion_factor = VASP_TO_THZ
    ph.run_mesh(mesh, is_mesh_symmetry=False)
    ph.run_total_dos()
    ph.run_thermal_properties(
        t_min=args.t_min, t_max=args.t_max, t_step=args.t_step
    )
    return ph, ph.get_total_dos_dict(), ph.get_thermal_properties_dict()


def write_csv(path: Path, header: list[str], columns: list[np.ndarray]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(zip(*columns))


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    plot_out = output_dir / "thermal_properties_reproduced.png"
    thermal_out = output_dir / "thermal_properties.csv"
    dos_out = output_dir / "phonon_dos.csv"
    metrics_out = output_dir / "thermal_metrics.json"
    outputs = [plot_out, thermal_out, dos_out, metrics_out]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise SystemExit("error: refusing to overwrite:\n  " + "\n  ".join(existing))
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh = tuple(args.mesh)
    ph, dos, thermal = calculate(args.input, mesh, args)
    historical, historical_dos, historical_thermal = calculate(
        args.historical_yaml, mesh, args
    )

    frequencies_mev = np.asarray(dos["frequency_points"]) * THZ_TO_MEV
    dos_values = np.asarray(dos["total_dos"])
    temperatures = np.asarray(thermal["temperatures"])
    free_energy = np.asarray(thermal["free_energy"])
    entropy = np.asarray(thermal["entropy"])
    heat_capacity = np.asarray(thermal["heat_capacity"])
    n_atoms = len(ph.primitive)
    cv_per_atom_kb = heat_capacity / (n_atoms * GAS_CONSTANT)

    old_temperatures = np.asarray(historical_thermal["temperatures"])
    if not np.array_equal(temperatures, old_temperatures):
        raise SystemExit("error: historical and reproduced temperature grids differ")
    old_frequencies_mev = (
        np.asarray(historical_dos["frequency_points"]) * THZ_TO_MEV
    )
    if frequencies_mev.shape != old_frequencies_mev.shape or not np.allclose(
        frequencies_mev, old_frequencies_mev, atol=1e-10
    ):
        raise SystemExit("error: historical and reproduced DOS grids differ")

    write_csv(
        thermal_out,
        [
            "temperature_K",
            "free_energy_kJ_per_mol_cell",
            "entropy_J_per_K_mol_cell",
            "heat_capacity_J_per_K_mol_cell",
            "heat_capacity_kB_per_atom",
        ],
        [temperatures, free_energy, entropy, heat_capacity, cv_per_atom_kb],
    )
    write_csv(
        dos_out,
        ["frequency_meV", "total_DOS_per_meV"],
        [frequencies_mev, dos_values / THZ_TO_MEV],
    )

    old_cv = np.asarray(historical_thermal["heat_capacity"])
    old_entropy = np.asarray(historical_thermal["entropy"])
    old_free_energy = np.asarray(historical_thermal["free_energy"])
    metrics = {
        "runtime_phonopy_version": phonopy.__version__,
        "input_yaml": str(args.input.resolve()),
        "force_constants_shape": list(np.asarray(ph.force_constants).shape),
        "mesh": list(mesh),
        "mesh_symmetry": False,
        "temperature_range_K": [args.t_min, args.t_max, args.t_step],
        "primitive_atoms": n_atoms,
        "frequency_unit": "meV",
        "free_energy_unit": "kJ/mol primitive cell",
        "entropy_unit": "J/K/mol primitive cell",
        "heat_capacity_unit": "J/K/mol primitive cell",
        "heat_capacity_normalization": "Cv / (primitive_atoms * R) = kB/atom",
        "cv_at_tmax_kB_per_atom": float(cv_per_atom_kb[-1]),
        "cv_tmax_fraction_of_3kB": float(cv_per_atom_kb[-1] / 3.0),
        "cv_tmax_below_3kB_per_atom": float(3.0 - cv_per_atom_kb[-1]),
        "dos_integral_modes_per_primitive_cell": float(
            np.trapz(dos_values, np.asarray(dos["frequency_points"]))
        ),
        "historical_figure_raw_data_available": False,
        "historical_yaml_same_grid": True,
        "historical_yaml_max_abs_cv_difference_J_per_K_mol": float(
            np.max(np.abs(heat_capacity - old_cv))
        ),
        "historical_yaml_max_abs_entropy_difference_J_per_K_mol": float(
            np.max(np.abs(entropy - old_entropy))
        ),
        "historical_yaml_max_abs_free_energy_difference_kJ_per_mol": float(
            np.max(np.abs(free_energy - old_free_energy))
        ),
    }
    metrics_out.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    figure, axes = plt.subplots(2, 2, figsize=(9, 5.2), dpi=200)
    axis = axes[0, 0]
    axis.plot(frequencies_mev, dos_values / THZ_TO_MEV, color="black")
    axis.fill_between(frequencies_mev, dos_values / THZ_TO_MEV, color="0.8")
    axis.set(xlabel="Frequency (meV)", ylabel="DOS (1/meV)", title="(a) Phonon DOS")
    axis.set_xlim(left=0)
    axis.set_ylim(bottom=0)

    axis = axes[0, 1]
    axis.plot(temperatures, cv_per_atom_kb, label="Calculated")
    axis.axhline(3.0, color="red", linestyle="--", label=r"$3k_B$/atom")
    axis.set(
        xlabel="Temperature (K)",
        ylabel=r"$C_V$ ($k_B$/atom)",
        title="(b) Heat capacity",
    )
    axis.set_xlim(args.t_min, args.t_max)
    axis.set_ylim(0, 3.5)
    axis.legend(frameon=False)

    axis = axes[1, 0]
    axis.plot(temperatures, entropy)
    axis.set(
        xlabel="Temperature (K)",
        ylabel="Entropy (J/K/mol cell)",
        title="(c) Entropy",
    )
    axis.set_xlim(args.t_min, args.t_max)
    axis.set_ylim(bottom=0)

    axis = axes[1, 1]
    axis.plot(temperatures, free_energy)
    axis.set(
        xlabel="Temperature (K)",
        ylabel="Free energy (kJ/mol cell)",
        title="(d) Helmholtz free energy",
    )
    axis.set_xlim(args.t_min, args.t_max)

    figure.tight_layout()
    figure.savefig(plot_out, dpi=300)
    plt.close(figure)
    print(json.dumps(metrics, indent=2))
    print(f"saved outputs in: {output_dir}")


if __name__ == "__main__":
    main()
