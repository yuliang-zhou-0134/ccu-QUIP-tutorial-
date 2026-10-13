#!/usr/bin/env python3
"""Create an extended-XYZ file containing only energy labels."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator
from ase.io import read, write


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strip force/stress labels and retain total energies only."
    )
    parser.add_argument("--input", type=Path, required=True, help="Input extended XYZ")
    parser.add_argument("--output", type=Path, required=True, help="Output extended XYZ")
    return parser.parse_args()


def reference_energy(atoms: Atoms) -> float:
    if atoms.calc is not None and "energy" in atoms.calc.results:
        energy = atoms.calc.results["energy"]
    elif "energy" in atoms.info:
        energy = atoms.info["energy"]
    else:
        raise KeyError("A frame has no total-energy label named 'energy'.")

    value = float(energy)
    if not np.isfinite(value):
        raise ValueError("A frame contains a non-finite energy label.")
    return value


def energy_only_copy(atoms: Atoms, energy: float) -> Atoms:
    # Rebuild the Atoms object so force/stress/virial labels cannot leak into
    # either atoms.arrays, atoms.info, or the attached calculator results.
    clean = Atoms(
        symbols=atoms.get_chemical_symbols(),
        positions=atoms.positions.copy(),
        cell=atoms.cell.copy(),
        pbc=atoms.pbc.copy(),
    )
    clean.calc = SinglePointCalculator(clean, energy=energy)
    return clean


def main() -> None:
    args = parse_args()
    frames = read(args.input, index=":")
    if not frames:
        raise ValueError(f"No structures found in {args.input}")

    clean_frames = [energy_only_copy(atoms, reference_energy(atoms)) for atoms in frames]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, clean_frames, format="extxyz")

    # Read the written file back: this verifies what gap_fit will actually see.
    checked = read(args.output, index=":")
    for index, atoms in enumerate(checked):
        results = set(atoms.calc.results) if atoms.calc is not None else set()
        if results != {"energy"}:
            raise RuntimeError(
                f"Frame {index} has unexpected labels after writing: {sorted(results)}"
            )

    print(f"Wrote {len(checked)} energy-only structures to {args.output}")


if __name__ == "__main__":
    main()
