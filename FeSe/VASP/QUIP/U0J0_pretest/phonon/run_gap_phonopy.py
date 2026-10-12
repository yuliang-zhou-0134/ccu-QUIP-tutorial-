#!/usr/bin/env python3
"""Run the historical GAP -> finite-displacement Phonopy workflow.

The default 4x4x4 run is intentionally not launched by validation scripts.
It evaluates 256-atom cells and should be submitted according to local HPC rules.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from ase import Atoms
from ase.filters import FrechetCellFilter
from ase.io import read
from ase.optimize import BFGS
from phonopy import Phonopy
from phonopy.structure.atoms import PhonopyAtoms


ROOT = Path(__file__).resolve().parents[1]
THZ_TO_MEV = 4.135667696


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structure", type=Path, default=ROOT / "phonon" / "POSCAR")
    parser.add_argument("--model", type=Path, default=ROOT / "model" / "csc_ver.xml")
    parser.add_argument("--supercell", type=int, nargs=3, default=(4, 4, 4))
    parser.add_argument("--displacement", type=float, default=0.01)
    parser.add_argument("--fmax", type=float, default=1.0e-6)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "phonon" / "output"
    )
    parser.add_argument(
        "--skip-relax",
        action="store_true",
        help="use the input cell directly instead of historical hydrostatic relaxation",
    )
    parser.add_argument("--force-overwrite", action="store_true")
    return parser.parse_args()


def require_new(paths: list[Path], force_overwrite: bool) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing and not force_overwrite:
        joined = "\n  ".join(existing)
        raise SystemExit(
            "error: refusing to overwrite existing output(s):\n  "
            f"{joined}\nUse a new --output-dir or pass --force-overwrite."
        )


def band_paths() -> tuple[list[np.ndarray], list[str]]:
    gamma = np.array([0.0, 0.0, 0.0])
    x = np.array([0.5, 0.0, 0.0])
    m = np.array([0.5, 0.5, 0.0])
    z = np.array([0.0, 0.0, 0.5])
    r = np.array([0.5, 0.0, 0.5])
    a = np.array([0.5, 0.5, 0.5])
    nodes = [gamma, x, m, gamma, z, r, a, z]
    paths = [np.linspace(start, end, 100) for start, end in zip(nodes, nodes[1:])]
    labels = [r"$\Gamma$", "X", "M", r"$\Gamma$", "Z", "R", "A", "Z"]
    return paths, labels


def save_band_plot(phonon: Phonopy, path: Path) -> None:
    paths, labels = band_paths()
    phonon.run_band_structure(paths, labels=labels)
    data = phonon.get_band_structure_dict()

    figure, axis = plt.subplots(figsize=(9, 5.5))
    boundaries = []
    for distances, frequencies in zip(data["distances"], data["frequencies"]):
        frequencies_mev = np.asarray(frequencies) * THZ_TO_MEV
        for branch in frequencies_mev.T:
            axis.plot(distances, branch, color="#1769aa", linewidth=1.2)
        boundaries.append(float(distances[0]))
    boundaries.append(float(data["distances"][-1][-1]))
    for value in boundaries:
        axis.axvline(value, color="0.75", linewidth=0.8)
    axis.axhline(0.0, color="0.35", linewidth=0.8)
    axis.set_xticks(boundaries, labels)
    axis.set_ylabel("Frequency (meV)")
    axis.set_title("FeSe GAP phonon dispersion")
    figure.tight_layout()
    figure.savefig(path, dpi=300)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    try:
        from quippy.potential import Potential
    except ModuleNotFoundError as exc:
        print(
            "error: quippy is not importable. Use the Python bindings from the "
            "same QUIP installation that reads the bundled XML.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    output_dir = args.output_dir.resolve()
    yaml_path = output_dir / "csc_ver_reproduced.yaml"
    plot_path = output_dir / "phonon_gap_reproduced.png"
    relaxed_path = output_dir / "CONTCAR_gap_reproduced"
    log_path = output_dir / "relax.log"
    trajectory_path = output_dir / "relax.traj"
    require_new(
        [yaml_path, plot_path, relaxed_path, log_path, trajectory_path],
        args.force_overwrite,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    atoms = read(args.structure.resolve(), format="vasp")
    potential = Potential("IP GAP", param_filename=str(args.model.resolve()))
    atoms.calc = potential

    if not args.skip_relax:
        # This reproduces the historical plot_phonon.py choice: only an
        # isotropic (hydrostatic) cell strain is allowed during relaxation.
        cell_filter = FrechetCellFilter(atoms, hydrostatic_strain=True)
        optimizer = BFGS(
            cell_filter, trajectory=str(trajectory_path), logfile=str(log_path)
        )
        optimizer.run(fmax=args.fmax)
    from ase.io import write

    write(relaxed_path, atoms, format="vasp")

    unitcell = PhonopyAtoms(
        symbols=atoms.get_chemical_symbols(),
        cell=atoms.cell.array,
        scaled_positions=atoms.get_scaled_positions(),
    )
    phonon = Phonopy(unitcell, supercell_matrix=np.diag(args.supercell))
    phonon.generate_displacements(distance=args.displacement)
    displaced_cells = phonon.supercells_with_displacements

    perfect = Atoms(
        symbols=phonon.supercell.symbols,
        positions=phonon.supercell.positions,
        cell=phonon.supercell.cell,
        pbc=True,
    )
    perfect.calc = potential
    background_forces = perfect.get_forces()
    print(f"displaced supercells: {len(displaced_cells)}")
    print(f"atoms per supercell: {len(perfect)}")
    print(f"max background |force|: {np.abs(background_forces).max():.8f} eV/A")

    force_sets = []
    for index, cell in enumerate(displaced_cells, start=1):
        displaced = Atoms(
            symbols=cell.symbols,
            positions=cell.positions,
            cell=cell.cell,
            pbc=True,
        )
        displaced.calc = potential
        force_sets.append(displaced.get_forces() - background_forces)
        print(f"force calculation {index}/{len(displaced_cells)} complete")

    phonon.forces = force_sets
    phonon.produce_force_constants()
    phonon.symmetrize_force_constants()
    phonon.save(yaml_path, settings={"force_constants": True})
    save_band_plot(phonon, plot_path)
    print(f"saved: {yaml_path}")
    print(f"saved: {plot_path}")


if __name__ == "__main__":
    main()
