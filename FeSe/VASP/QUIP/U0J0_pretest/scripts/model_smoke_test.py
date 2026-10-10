#!/usr/bin/env python3
"""Evaluate one historical XYZ frame with the bundled GAP model."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
from ase.io import read


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=int, default=0, help="zero-based XYZ frame")
    parser.add_argument(
        "--data", type=Path, default=ROOT / "data" / "csc_data_74.xyz"
    )
    parser.add_argument(
        "--model", type=Path, default=ROOT / "model" / "csc_ver.xml"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from quippy.potential import Potential
    except ModuleNotFoundError as exc:
        print(
            "error: quippy is not importable in this Python environment. "
            "Install quippy-ase or expose the Python bindings from the matching "
            "QUIP build.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    atoms = read(args.data.resolve(), index=args.frame)
    reference_energy = atoms.get_potential_energy()
    atoms.calc = Potential("IP GAP", param_filename=str(args.model.resolve()))
    gap_energy = atoms.get_potential_energy()
    forces = atoms.get_forces()

    if not np.isfinite(gap_energy) or not np.isfinite(forces).all():
        raise SystemExit("error: GAP returned a non-finite energy or force")

    print(f"frame: {args.frame}")
    print(f"formula: {atoms.get_chemical_formula()} ({len(atoms)} atoms)")
    print(f"reference energy: {reference_energy:.10f} eV")
    print(f"GAP energy:       {gap_energy:.10f} eV")
    print(f"GAP-reference:    {gap_energy - reference_energy:.10f} eV")
    print(f"force array:      {forces.shape}")
    print(f"max |force|:      {np.abs(forces).max():.10f} eV/angstrom")


if __name__ == "__main__":
    main()
