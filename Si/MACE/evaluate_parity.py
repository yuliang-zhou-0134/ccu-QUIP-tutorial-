#!/usr/bin/env python3
"""Reproduce Si MACE energy/force/stress parity plots without retraining.

From repository root:
  python Si/MACE/evaluate_parity.py --model /path/to/stagetwo.model

Uses Si/train_smart.xyz and Si/test_smart.xyz. Writes new results under
Si/MACE/results/recomputed/; does not overwrite historical figures.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from ase.io import read

SI_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results" / "recomputed"


def rmse(ref, pred):
    a, b = np.asarray(ref, dtype=float), np.asarray(pred, dtype=float)
    return float(np.sqrt(np.mean((b - a) ** 2)))


def draw(ax, ref, pred, title, unit, label, subsample=False):
    ref, pred = np.asarray(ref), np.asarray(pred)
    x, y = ref, pred
    if subsample and len(x) > 1000:
        idx = np.random.default_rng(123).choice(len(x), 1000, replace=False)
        x, y = x[idx], y[idx]
    ax.scatter(x, y, alpha=0.45, s=8 if subsample else 16)
    lo = min(float(np.min(ref)), float(np.min(pred)))
    hi = max(float(np.max(ref)), float(np.max(pred)))
    ax.plot([lo, hi], [lo, hi], "k--", linewidth=1)
    ax.set_title(title)
    ax.set_xlabel(f"DFT ({unit})")
    ax.set_ylabel(f"MACE ({unit})")
    ax.grid(alpha=0.3, linestyle="--")
    ax.text(0.04, 0.95, label, transform=ax.transAxes, va="top")


def evaluate(path, calc, split, outdir):
    frames = read(str(path), index=":")
    if not frames:
        raise ValueError(f"No structures in {path}")
    er, ep, fr, fp, sr, sp = [], [], [], [], [], []
    stress_count = 0
    for atoms in frames:
        # Always collect reference labels before assigning the MACE calculator.
        e_dft = float(atoms.get_potential_energy()) / len(atoms)
        f_dft = np.asarray(atoms.get_forces(), dtype=float).ravel()
        try:
            s_dft = np.asarray(atoms.get_stress(voigt=True), dtype=float)
        except (RuntimeError, ValueError, NotImplementedError):
            s_dft = None

        predicted = atoms.copy()
        predicted.calc = calc
        e_ml = float(predicted.get_potential_energy()) / len(predicted)
        f_ml = np.asarray(predicted.get_forces(), dtype=float).ravel()
        er.append(e_dft)
        ep.append(e_ml)
        fr.extend(f_dft)
        fp.extend(f_ml)
        if s_dft is not None:
            s_ml = np.asarray(predicted.get_stress(voigt=True), dtype=float)
            sr.extend(s_dft)
            sp.extend(s_ml)
            stress_count += 1

    e_error = rmse(er, ep) * 1000
    f_error = rmse(fr, fp) * 1000
    s_error = rmse(sr, sp) if stress_count else None
    cols = 3 if stress_count else 2
    fig, ax = plt.subplots(1, cols, figsize=(6 * cols, 5))
    draw(ax[0], er, ep, f"{split}: Energy", "eV/atom", f"RMSE: {e_error:.2f} meV/atom")
    draw(ax[1], fr, fp, f"{split}: Force", "eV/Å", f"RMSE: {f_error:.2f} meV/Å", subsample=True)
    if stress_count:
        draw(ax[2], sr, sp, f"{split}: Stress (Voigt)", "eV/Å³",
             f"RMSE: {s_error:.4f} eV/Å³")
    fig.tight_layout()
    fig.savefig(outdir / f"{split.lower()}_parity.png", dpi=250, bbox_inches="tight")
    plt.close(fig)
    print(f"{split}: energy {e_error:.4f} meV/atom, force {f_error:.4f} meV/Å, stress {s_error}")
    return {
        "input_file": str(path),
        "structures": len(frames),
        "stress_labeled_structures": stress_count,
        "energy_rmse_meV_per_atom": e_error,
        "force_rmse_meV_per_A": f_error,
        "stress_rmse_eV_per_A3": s_error,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=Path, required=True, help="Trusted MACE .model checkpoint")
    p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    p.add_argument("--split", choices=["both", "train", "validation"], default="both")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    if not args.model.is_file():
        p.error(f"Model not found: {args.model}")

    import torch
    from mace.calculators import MACECalculator
    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device == "cuda" and not torch.cuda.is_available():
        p.error("CUDA unavailable; use --device cpu")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    calc = MACECalculator(model_paths=str(args.model), device=device, default_dtype="float64")
    results = {
        "model": args.model.name,
        "model_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
        "device": device,
        "note": "test_smart.xyz is validation, not an independent holdout. Stress uses ASE Voigt convention.",
        "datasets": {},
    }
    for key, path in {
        "train": SI_DIR / "train_smart.xyz",
        "validation": SI_DIR / "test_smart.xyz",
    }.items():
        if args.split != "both" and args.split != key:
            continue
        if not path.is_file():
            p.error(f"Missing XYZ: {path}")
        results["datasets"][key] = evaluate(path, calc, key.title(), args.output_dir)
    (args.output_dir / "metrics.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Results saved in {args.output_dir}")


if __name__ == "__main__":
    main()
