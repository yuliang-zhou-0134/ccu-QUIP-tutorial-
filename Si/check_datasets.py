#!/usr/bin/env python3
"""Inspect Si extended-XYZ sets and flag exact-ish duplicate geometries.

Run from any directory: python Si/check_datasets.py
This script does not train a model or change input files.
"""
import hashlib
from pathlib import Path

import numpy as np
from ase.io import read

ROOT = Path(__file__).resolve().parent


def geometry_signature(atoms):
    """Element order, cell and wrapped scaled positions (rounded to 1e-6)."""
    cell = np.asarray(atoms.cell.array, dtype=float)
    frac = np.asarray(atoms.get_scaled_positions(wrap=True), dtype=float)
    frac = np.mod(frac, 1.0)
    # Avoid different hashes for fractional coordinates near 0 and 1.
    frac[np.isclose(frac, 1.0, atol=1e-6)] = 0.0
    symbols = "|".join(atoms.get_chemical_symbols()).encode("utf-8")
    geometric = np.concatenate((cell.ravel(), frac.ravel()))
    rounded = np.round(geometric, 6).astype("<f8", copy=False)
    return hashlib.sha256(symbols + rounded.tobytes()).hexdigest()


def energy_label(atoms):
    if "energy" in atoms.info:
        return float(atoms.info["energy"])
    try:
        return float(atoms.get_potential_energy())
    except Exception as exc:
        raise ValueError("Missing reference energy label") from exc


def load(path):
    if not path.is_file():
        raise SystemExit(f"Missing file: {path}")
    frames = read(str(path), index=":")
    if not frames:
        raise SystemExit(f"No structures found: {path}")
    hashes = []
    for i, atoms in enumerate(frames):
        if not np.isfinite(np.asarray(atoms.positions)).all():
            raise SystemExit(f"{path.name}: frame {i} has non-finite positions")
        if not np.isfinite(atoms.cell.array).all():
            raise SystemExit(f"{path.name}: frame {i} has non-finite cell")
        if not np.isfinite(energy_label(atoms)):
            raise SystemExit(f"{path.name}: frame {i} has non-finite reference energy")
        hashes.append(geometry_signature(atoms))
    print(f"{path.name}: {len(frames)} frames, {len(set(hashes))} coordinate-distinct geometries")
    return hashes


def main():
    training = load(ROOT / "train_smart.xyz")
    validation = load(ROOT / "test_smart.xyz")
    overlap = set(training) & set(validation)
    print(f"Exact/rounded-coordinate train–validation overlap: {len(overlap)} geometries")
    print("Note: this check is sensitive to atom ordering; it is not symmetry-aware.")
    if overlap:
        raise SystemExit(
            "WARNING: train and validation sets share identical geometries. "
            "Revisit the split before claiming independent performance."
        )
    print("PASS: no identical ordered geometries found across the two sets")


if __name__ == "__main__":
    main()
