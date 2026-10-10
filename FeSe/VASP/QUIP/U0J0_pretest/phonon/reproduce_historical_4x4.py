#!/usr/bin/env python3
"""Recalculate the historical 4x4x4 Phonopy forces with the bundled GAP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import phonopy
from ase import Atoms
from phonopy import Phonopy, load
from phonopy.structure.atoms import PhonopyAtoms


ROOT = Path(__file__).resolve().parents[1]
VASP_TO_THZ = 15.633302
THZ_TO_MEV = 4.135667696


def band_path() -> tuple[list[np.ndarray], list[str]]:
    gamma = np.array([0.0, 0.0, 0.0])
    x = np.array([0.5, 0.0, 0.0])
    m = np.array([0.5, 0.5, 0.0])
    z = np.array([0.0, 0.0, 0.5])
    r = np.array([0.5, 0.0, 0.5])
    a = np.array([0.5, 0.5, 0.5])
    nodes = [gamma, x, m, gamma, z, r, a, z]
    labels = [r"$\Gamma$", "X", "M", r"$\Gamma$", "Z", "R", "A", "Z"]
    return [np.linspace(p, q, 100) for p, q in zip(nodes, nodes[1:])], labels


def dataset_displacements(ph) -> tuple[list[int], np.ndarray]:
    first_atoms = ph.dataset["first_atoms"]
    return (
        [int(entry["number"]) for entry in first_atoms],
        np.asarray([entry["displacement"] for entry in first_atoms]),
    )


def band_frequencies_mev(ph, paths: list[np.ndarray]) -> np.ndarray:
    ph.unit_conversion_factor = VASP_TO_THZ
    ph.run_band_structure(paths)
    return np.concatenate(ph.get_band_structure_dict()["frequencies"], axis=0) * THZ_TO_MEV


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--historical-yaml", type=Path, default=ROOT / "phonon" / "csc_ver.yaml"
    )
    parser.add_argument("--model", type=Path, default=ROOT / "model" / "csc_ver.xml")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "phonon" / "output_reproduction_4x4",
    )
    args = parser.parse_args()

    try:
        from quippy.potential import Potential
    except ModuleNotFoundError as exc:
        print("error: quippy is not importable", file=sys.stderr)
        raise SystemExit(2) from exc

    output_dir = args.output_dir.resolve()
    yaml_out = output_dir / "csc_ver_reproduced_4x4.yaml"
    plot_out = output_dir / "phonon_reproduced_4x4.png"
    compare_out = output_dir / "history_vs_reproduced.png"
    report_out = output_dir / "reproduction_metrics.json"
    outputs = [yaml_out, plot_out, compare_out, report_out]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise SystemExit("error: refusing to overwrite:\n  " + "\n  ".join(existing))
    output_dir.mkdir(parents=True, exist_ok=True)

    historical = load(args.historical_yaml.resolve(), produce_fc=True)
    historical.unit_conversion_factor = VASP_TO_THZ
    matrix = np.asarray(historical.supercell_matrix, dtype=int)
    if not np.array_equal(matrix, np.diag([4, 4, 4])):
        raise SystemExit(f"error: historical supercell is not 4x4x4: {matrix.tolist()}")
    old_numbers, old_displacements = dataset_displacements(historical)
    displacement_distance = float(np.linalg.norm(old_displacements[0]))
    if not np.allclose(np.linalg.norm(old_displacements, axis=1), 0.01, atol=1e-12):
        raise SystemExit("error: historical displacements are not all 0.01 angstrom")

    unitcell = PhonopyAtoms(
        symbols=historical.unitcell.symbols,
        cell=historical.unitcell.cell,
        scaled_positions=historical.unitcell.scaled_positions,
    )
    reproduced = Phonopy(unitcell, supercell_matrix=matrix)
    reproduced.generate_displacements(distance=displacement_distance)
    new_numbers, new_displacements = dataset_displacements(reproduced)
    if old_numbers != new_numbers or not np.allclose(
        old_displacements, new_displacements, atol=1e-12
    ):
        raise SystemExit(
            "error: regenerated displacement dataset differs from historical YAML"
        )

    potential = Potential("IP GAP", param_filename=str(args.model.resolve()))
    perfect = Atoms(
        symbols=reproduced.supercell.symbols,
        positions=reproduced.supercell.positions,
        cell=reproduced.supercell.cell,
        pbc=True,
    )
    perfect.calc = potential
    background = perfect.get_forces()
    if not np.isfinite(background).all():
        raise SystemExit("error: non-finite background force")
    print(f"displaced supercells: {len(reproduced.supercells_with_displacements)}")
    print(f"atoms per supercell: {len(perfect)}")
    print(f"max background |force component|: {np.abs(background).max():.12e} eV/A")

    forces = []
    for index, cell in enumerate(reproduced.supercells_with_displacements, start=1):
        atoms = Atoms(
            symbols=cell.symbols,
            positions=cell.positions,
            cell=cell.cell,
            pbc=True,
        )
        atoms.calc = potential
        force = atoms.get_forces() - background
        if not np.isfinite(force).all():
            raise SystemExit(f"error: non-finite force in displacement {index}")
        forces.append(force)
        print(f"force calculation {index}/{len(reproduced.supercells_with_displacements)} complete")

    reproduced.forces = forces
    reproduced.produce_force_constants()
    reproduced.symmetrize_force_constants()
    if not np.isfinite(reproduced.force_constants).all():
        raise SystemExit("error: non-finite force constants")
    reproduced.save(yaml_out, settings={"force_constants": True})

    reloaded = load(yaml_out, produce_fc=True)
    if not np.isfinite(reloaded.force_constants).all():
        raise SystemExit("error: saved YAML reload produced non-finite force constants")

    paths, labels = band_path()
    old_band = band_frequencies_mev(historical, paths)
    new_band = band_frequencies_mev(reloaded, paths)
    if old_band.shape != new_band.shape:
        raise SystemExit(f"error: band shape mismatch {old_band.shape} != {new_band.shape}")
    difference = new_band - old_band
    force_difference = np.asarray(forces) - np.asarray(historical.forces)

    old_gz = old_band[300:400]
    new_gz = new_band[300:400]
    old_gz_span = old_gz.max(axis=0) - old_gz.min(axis=0)
    new_gz_span = new_gz.max(axis=0) - new_gz.min(axis=0)
    report = {
        "runtime_phonopy_version": phonopy.__version__,
        "supercell_matrix": matrix.tolist(),
        "atoms_per_supercell": len(perfect),
        "displaced_supercells": len(forces),
        "displacement_distance_A": displacement_distance,
        "background_force_max_abs_component_eV_per_A": float(np.abs(background).max()),
        "forces_all_finite": bool(np.isfinite(forces).all()),
        "force_constants_shape": list(np.asarray(reloaded.force_constants).shape),
        "force_constants_all_finite": bool(np.isfinite(reloaded.force_constants).all()),
        "yaml_reload": True,
        "frequency_unit": "meV",
        "q_path": ["Gamma", "X", "M", "Gamma", "Z", "R", "A", "Z"],
        "points_per_segment": 100,
        "band_array_shape": list(old_band.shape),
        "max_abs_force_difference_eV_per_A": float(np.abs(force_difference).max()),
        "rms_force_difference_eV_per_A": float(np.sqrt(np.mean(force_difference**2))),
        "max_abs_frequency_difference_meV": float(np.abs(difference).max()),
        "mean_abs_frequency_difference_meV": float(np.mean(np.abs(difference))),
        "rms_frequency_difference_meV": float(np.sqrt(np.mean(difference**2))),
        "historical_minimum_frequency_meV": float(old_band.min()),
        "reproduced_minimum_frequency_meV": float(new_band.min()),
        "minimum_frequency_difference_meV": float(new_band.min() - old_band.min()),
        "historical_negative_frequency_values": int(np.count_nonzero(old_band < 0.0)),
        "reproduced_negative_frequency_values": int(np.count_nonzero(new_band < 0.0)),
        "historical_frequency_values_below_minus_0_1_meV": int(
            np.count_nonzero(old_band < -0.1)
        ),
        "reproduced_frequency_values_below_minus_0_1_meV": int(
            np.count_nonzero(new_band < -0.1)
        ),
        "historical_Gamma_Z_max_branch_span_meV": float(old_gz_span.max()),
        "reproduced_Gamma_Z_max_branch_span_meV": float(new_gz_span.max()),
        "Gamma_Z_max_span_difference_meV": float(
            np.max(np.abs(new_gz_span - old_gz_span))
        ),
    }
    report_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    x_axis = np.concatenate([np.linspace(i, i + 1, 100) for i in range(7)])
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for branch in new_band.T:
        ax.plot(x_axis, branch, color="#1769aa", linewidth=1.2)
    for boundary in range(8):
        ax.axvline(boundary, color="0.75", linewidth=0.8)
    ax.axhline(0.0, color="0.35", linewidth=0.8)
    ax.set_xticks(range(8), labels)
    ax.set_xlim(0, 7)
    ax.set_ylabel("Frequency (meV)")
    ax.set_title("Reproduced FeSe GAP phonons (4x4x4)")
    fig.tight_layout()
    fig.savefig(plot_out, dpi=300)
    plt.close(fig)

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    for branch_index in range(old_band.shape[1]):
        top.plot(
            x_axis,
            old_band[:, branch_index],
            color="black",
            linestyle="--",
            linewidth=1.2,
            label="historical" if branch_index == 0 else None,
        )
        top.plot(
            x_axis,
            new_band[:, branch_index],
            color="#d62728",
            linewidth=0.9,
            label="reproduced" if branch_index == 0 else None,
        )
        bottom.plot(x_axis, difference[:, branch_index], color="#1769aa", linewidth=0.8)
    for axis in (top, bottom):
        for boundary in range(8):
            axis.axvline(boundary, color="0.75", linewidth=0.8)
        axis.axhline(0.0, color="0.35", linewidth=0.8)
    top.set_ylabel("Frequency (meV)")
    top.legend(frameon=False)
    bottom.set_ylabel("new - history (meV)")
    bottom.set_xticks(range(8), labels)
    bottom.set_xlim(0, 7)
    fig.tight_layout()
    fig.savefig(compare_out, dpi=300)
    plt.close(fig)

    print(json.dumps(report, indent=2))
    for path in outputs:
        print(f"saved: {path}")


if __name__ == "__main__":
    main()
