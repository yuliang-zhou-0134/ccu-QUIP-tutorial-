#!/usr/bin/env python3
"""Validate a retrained GAP against labels and the preserved historical GAP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from ase.io import read
from quippy.potential import Potential


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data", type=Path, default=ROOT / "data" / "csc_data_74.xyz"
    )
    parser.add_argument(
        "--old-model", type=Path, default=ROOT / "model" / "csc_ver.xml"
    )
    parser.add_argument(
        "--new-model",
        type=Path,
        default=ROOT / "training" / "output" / "csc_ver_retrained.xml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "training" / "output" / "validation_metrics.json",
    )
    return parser.parse_args()


def metrics(values: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(np.mean(np.abs(values))),
        "rmse": float(np.sqrt(np.mean(values**2))),
        "max_abs": float(np.max(np.abs(values))),
    }


def evaluate(frames, potential: Potential) -> tuple[np.ndarray, np.ndarray]:
    energies = []
    forces = []
    for source in frames:
        atoms = source.copy()
        atoms.calc = potential
        energies.append(atoms.get_potential_energy())
        forces.append(atoms.get_forces())
    energies_array = np.asarray(energies)
    forces_array = np.asarray(forces)
    if not np.isfinite(energies_array).all() or not np.isfinite(forces_array).all():
        raise SystemExit("error: model produced a non-finite energy or force")
    return energies_array, forces_array


def check_sparse_files(model: Path) -> list[str]:
    root = ET.parse(model).getroot()
    checked = []
    for element in root.iter():
        filename = element.attrib.get("sparseX_filename")
        expected_md5 = element.attrib.get("sparseX_md5sum")
        if filename is None:
            continue
        sparse = model.parent / Path(filename).name
        if not sparse.is_file():
            raise SystemExit(f"error: referenced SparseX is missing: {sparse}")
        actual_md5 = hashlib.md5(sparse.read_bytes()).hexdigest()
        if expected_md5 != actual_md5:
            raise SystemExit(f"error: SparseX MD5 mismatch: {sparse}")
        checked.append(sparse.name)
    if not checked:
        raise SystemExit("error: retrained XML does not reference any SparseX files")
    return checked


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"error: refusing to overwrite {output}")
    if not args.new_model.is_file():
        raise SystemExit(f"error: retrained model not found: {args.new_model}")
    sparse_files = check_sparse_files(args.new_model.resolve())

    frames = read(args.data.resolve(), index=":")
    reference = np.asarray([atoms.get_potential_energy() for atoms in frames])
    atom_counts = np.asarray([len(atoms) for atoms in frames])
    if len(frames) != 74 or set(atom_counts) != {32} or not np.isfinite(reference).all():
        raise SystemExit("error: expected 74 finite-energy frames with 32 atoms each")

    old_potential = Potential("IP GAP", param_filename=str(args.old_model.resolve()))
    new_potential = Potential("IP GAP", param_filename=str(args.new_model.resolve()))
    old_energy, old_forces = evaluate(frames, old_potential)
    new_energy, new_forces = evaluate(frames, new_potential)

    # A repeated frame-0 evaluation is a low-cost determinism smoke test.
    repeat = frames[0].copy()
    repeat.calc = new_potential
    repeat_energy = repeat.get_potential_energy()
    repeat_forces = repeat.get_forces()

    report = {
        "frames": len(frames),
        "atoms_per_frame": 32,
        "energy_unit": "eV/configuration",
        "force_unit": "eV/angstrom",
        "all_old_energies_and_forces_finite": True,
        "all_new_energies_and_forces_finite": True,
        "old_forces_shape": list(old_forces.shape),
        "new_forces_shape": list(new_forces.shape),
        "new_model_referenced_sparse_files": sparse_files,
        "new_model_sparse_md5_all_match": True,
        "old_minus_reference_energy": metrics(old_energy - reference),
        "new_minus_reference_energy": metrics(new_energy - reference),
        "new_minus_reference_energy_per_atom": metrics(
            (new_energy - reference) / atom_counts
        ),
        "new_minus_old_energy": metrics(new_energy - old_energy),
        "new_minus_old_force_components": metrics(new_forces - old_forces),
        "new_model_repeat_frame0_energy_abs_difference": float(
            abs(repeat_energy - new_energy[0])
        ),
        "new_model_repeat_frame0_force_max_abs_difference": float(
            np.max(np.abs(repeat_forces - new_forces[0]))
        ),
        "interpretation": (
            "Energy residuals are in-sample because the 74 energy labels are the "
            "training set. Forces have no reference labels and are compared only "
            "between the new and historical energy-only GAPs."
        ),
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
