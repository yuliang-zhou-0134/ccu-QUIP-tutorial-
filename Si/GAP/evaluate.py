#!/usr/bin/env python3
"""Evaluate the Si energy-only GAP on training and/or validation data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from ase.io import read
from ase.stress import full_3x3_to_voigt_6_stress


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = SCRIPT_DIR / "model" / "GAP_Si_EnergyOnly.xml"
DEFAULT_TRAIN = SCRIPT_DIR.parent / "train_smart.xyz"
DEFAULT_VALIDATION = SCRIPT_DIR.parent / "test_smart.xyz"
EXPECTED_COUNTS = {"training": 190, "validation": 22}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--train-file", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--validation-file", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument(
        "--split",
        choices=("training", "validation", "both"),
        default="both",
        help="Dataset(s) to evaluate (default: both)",
    )
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR / "results")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def value_from_atoms(atoms: Any, name: str) -> Any | None:
    if atoms.calc is not None and name in atoms.calc.results:
        return atoms.calc.results[name]
    if name in atoms.info:
        return atoms.info[name]
    if name in atoms.arrays:
        return atoms.arrays[name]
    return None


def as_voigt6(value: Any, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape == (6,):
        result = array.copy()
    elif array.shape == (3, 3):
        if not np.allclose(array, array.T, rtol=1e-7, atol=1e-10):
            raise ValueError(f"{label} tensor is not symmetric")
        result = full_3x3_to_voigt_6_stress(array)
    else:
        raise ValueError(f"{label} must have shape (6,) or (3, 3), got {array.shape}")
    if not np.isfinite(result).all():
        raise ValueError(f"{label} contains non-finite values")
    return result


def reference_stress(atoms: Any) -> np.ndarray:
    stress = value_from_atoms(atoms, "stress")
    if stress is not None:
        # Existing XYZ files store stress in eV/A^3. ASE maps a 3x3 tensor to
        # [xx, yy, zz, yz, xz, xy], with positive values meaning tension.
        return as_voigt6(stress, "stress")

    virial = value_from_atoms(atoms, "virial")
    if virial is None:
        raise KeyError("No reference stress or virial label found")
    volume = float(atoms.get_volume())
    if not np.isfinite(volume) or volume <= 0.0:
        raise ValueError(f"Invalid cell volume for virial conversion: {volume}")
    # ASE stress uses sigma = -virial / volume. Virial is in eV, so the
    # resulting stress unit is eV/A^3.
    return -as_voigt6(virial, "virial") / volume


def rmse(reference: np.ndarray, prediction: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(reference - prediction))))


def evaluate_dataset(calc: Any, path: Path, split: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    frames = read(path, index=":")
    expected = EXPECTED_COUNTS[split]
    if len(frames) != expected:
        raise ValueError(f"{split} should contain {expected} structures, found {len(frames)}")

    ref_energy: list[float] = []
    pred_energy: list[float] = []
    ref_forces: list[np.ndarray] = []
    pred_forces: list[np.ndarray] = []
    ref_stresses: list[np.ndarray] = []
    pred_stresses: list[np.ndarray] = []

    for index, atoms in enumerate(frames):
        energy = value_from_atoms(atoms, "energy")
        forces = value_from_atoms(atoms, "forces")
        if energy is None or forces is None:
            raise KeyError(f"Frame {index} in {path} lacks energy or forces")

        energy_value = float(energy) / len(atoms)
        force_values = np.asarray(forces, dtype=float)
        if force_values.shape != (len(atoms), 3):
            raise ValueError(f"Frame {index} forces have shape {force_values.shape}")
        stress_values = reference_stress(atoms)
        if not np.isfinite(energy_value) or not np.isfinite(force_values).all():
            raise ValueError(f"Frame {index} has non-finite reference values")

        ref_energy.append(energy_value)
        ref_forces.append(force_values.reshape(-1))
        ref_stresses.append(stress_values)

        # Install the GAP calculator only after all DFT reference values have
        # been copied. This is the supported ASE API (not set_calculator()).
        atoms.calc = calc
        gap_energy = atoms.get_potential_energy() / len(atoms)
        gap_forces = atoms.get_forces()
        gap_stress = atoms.get_stress(voigt=True)
        if not (
            np.isfinite(gap_energy)
            and np.isfinite(gap_forces).all()
            and np.isfinite(gap_stress).all()
        ):
            raise ValueError(f"Frame {index} has non-finite GAP predictions")

        pred_energy.append(float(gap_energy))
        pred_forces.append(gap_forces.reshape(-1))
        pred_stresses.append(gap_stress)

        if (index + 1) % 25 == 0 or index + 1 == len(frames):
            print(f"{split}: evaluated {index + 1}/{len(frames)} structures")

    arrays = {
        "energy_reference": np.asarray(ref_energy),
        "energy_prediction": np.asarray(pred_energy),
        "force_reference": np.concatenate(ref_forces),
        "force_prediction": np.concatenate(pred_forces),
        "stress_reference": np.concatenate(ref_stresses),
        "stress_prediction": np.concatenate(pred_stresses),
    }
    metrics = {
        "dataset_type": split,
        "source_file": path.name,
        "structures": len(frames),
        "atoms": int(sum(len(atoms) for atoms in frames)),
        "energy_rmse_meV_per_atom": 1000.0
        * rmse(arrays["energy_reference"], arrays["energy_prediction"]),
        "force_rmse_eV_per_A": rmse(arrays["force_reference"], arrays["force_prediction"]),
        "stress_rmse_eV_per_A3": rmse(
            arrays["stress_reference"], arrays["stress_prediction"]
        ),
        "stress_components": "ASE Voigt [xx, yy, zz, yz, xz, xy]",
    }
    return metrics, arrays


def parity_plot(split: str, metrics: dict[str, Any], arrays: dict[str, np.ndarray], output: Path) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(15, 4.6), dpi=150)
    title_split = "Training" if split == "training" else "Validation"
    figure.suptitle(f"Si GAP — Energy-only {title_split}", fontsize=15)

    panels = (
        ("energy", "Energy (eV/atom)", f"RMSE = {metrics['energy_rmse_meV_per_atom']:.2f} meV/atom", 8),
        ("force", "Force (eV/Å)", f"RMSE = {metrics['force_rmse_eV_per_A']:.3f} eV/Å", 3),
        ("stress", "Stress (eV/Å³)", f"RMSE = {metrics['stress_rmse_eV_per_A3']:.3f} eV/Å³", 8),
    )
    colors = ("#2458A6", "#C43B3B", "#2D7D46")
    for axis, (key, label, subtitle, size), color in zip(axes, panels, colors):
        reference = arrays[f"{key}_reference"]
        prediction = arrays[f"{key}_prediction"]
        low = float(min(reference.min(), prediction.min()))
        high = float(max(reference.max(), prediction.max()))
        padding = 0.04 * (high - low) if high > low else 1.0
        limits = (low - padding, high + padding)
        axis.scatter(reference, prediction, s=size, alpha=0.32, color=color, edgecolors="none")
        axis.plot(limits, limits, "k--", linewidth=1)
        axis.set_xlim(limits)
        axis.set_ylim(limits)
        axis.set_xlabel(f"DFT {label}")
        axis.set_ylabel(f"GAP {label}")
        axis.set_title(f"{label.split(' (')[0]}\n{subtitle}")
        axis.grid(alpha=0.25, linestyle=":")

    figure.tight_layout(rect=(0, 0, 1, 0.93))
    figure.savefig(output, dpi=300)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    model = args.model.resolve()
    if not model.is_file():
        raise FileNotFoundError(model)

    from quippy.potential import Potential

    calc = Potential(param_filename=str(model))
    selected = ("training", "validation") if args.split == "both" else (args.split,)
    paths = {"training": args.train_file, "validation": args.validation_file}
    args.output_dir.mkdir(parents=True, exist_ok=True)

    datasets: dict[str, Any] = {}
    for split in selected:
        metrics, arrays = evaluate_dataset(calc, paths[split], split)
        datasets[split] = metrics
        parity_plot(split, metrics, arrays, args.output_dir / f"{split}_parity.png")
        print(
            f"{split}: E={metrics['energy_rmse_meV_per_atom']:.5f} meV/atom, "
            f"F={metrics['force_rmse_eV_per_A']:.6f} eV/Å, "
            f"stress={metrics['stress_rmse_eV_per_A3']:.6f} eV/Å³"
        )

    sparse_files = sorted(model.parent.glob(f"{model.name}.sparseX.*"))
    report = {
        "model": {
            "name": model.name,
            "sha256": sha256(model),
            "fit_type": "from-scratch GAP, energy-only supervision",
            "sparse_files": [
                {"name": path.name, "sha256": sha256(path)} for path in sparse_files
            ],
        },
        "reference_stress": {
            "unit": "eV/A^3",
            "sign": "ASE convention: positive is tensile",
            "voigt_order": ["xx", "yy", "zz", "yz", "xz", "xy"],
            "virial_conversion_if_needed": "stress = -virial / volume",
        },
        "datasets": datasets,
    }
    json_name = "metrics.json" if args.split == "both" else f"{args.split}_metrics.json"
    with (args.output_dir / json_name).open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
