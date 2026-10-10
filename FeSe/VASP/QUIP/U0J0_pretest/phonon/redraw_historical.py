#!/usr/bin/env python3
"""Redraw the historical 4x4x4 Phonopy band structure without GAP calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import phonopy
from phonopy import load


ROOT = Path(__file__).resolve().parents[1]
THZ_TO_MEV = 4.135667696
VASP_TO_THZ = 15.633302


def band_path() -> tuple[list[np.ndarray], list[str], list[str]]:
    gamma = np.array([0.0, 0.0, 0.0])
    x = np.array([0.5, 0.0, 0.0])
    m = np.array([0.5, 0.5, 0.0])
    z = np.array([0.0, 0.0, 0.5])
    r = np.array([0.5, 0.0, 0.5])
    a = np.array([0.5, 0.5, 0.5])
    nodes = [gamma, x, m, gamma, z, r, a, z]
    labels = [r"$\Gamma$", "X", "M", r"$\Gamma$", "Z", "R", "A", "Z"]
    plain_labels = ["Gamma", "X", "M", "Gamma", "Z", "R", "A", "Z"]
    return [np.linspace(p, q, 100) for p, q in zip(nodes, nodes[1:])], labels, plain_labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "phonon" / "csc_ver.yaml")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "phonon" / "output_history_redraw"
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    outputs = [
        output_dir / "historical_phonon_redrawn.png",
        output_dir / "historical_band_frequencies_meV.npz",
        output_dir / "historical_metadata.json",
    ]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise SystemExit("error: refusing to overwrite:\n  " + "\n  ".join(existing))
    output_dir.mkdir(parents=True, exist_ok=True)

    ph = load(args.input.resolve(), produce_fc=True)
    ph.unit_conversion_factor = VASP_TO_THZ
    paths, labels, plain_labels = band_path()
    ph.run_band_structure(paths)
    band = ph.get_band_structure_dict()
    frequencies_mev = np.concatenate(band["frequencies"], axis=0) * THZ_TO_MEV
    qpoints = np.concatenate(band["qpoints"], axis=0)
    x_axis = np.concatenate([np.linspace(i, i + 1, 100) for i in range(7)])

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for branch in frequencies_mev.T:
        ax.plot(x_axis, branch, color="#1769aa", linewidth=1.2)
    for boundary in range(8):
        ax.axvline(boundary, color="0.75", linewidth=0.8)
    ax.axhline(0.0, color="0.35", linewidth=0.8)
    ax.set_xticks(range(8), labels)
    ax.set_xlim(0, 7)
    ax.set_ylabel("Frequency (meV)")
    ax.set_title("Historical FeSe GAP phonons (4x4x4)")
    fig.tight_layout()
    fig.savefig(outputs[0], dpi=300)
    plt.close(fig)

    np.savez_compressed(outputs[1], qpoints=qpoints, frequencies_meV=frequencies_mev)
    dataset = ph.dataset["first_atoms"]
    metadata = {
        "runtime_phonopy_version": phonopy.__version__,
        "yaml_recorded_phonopy_version": "3.2.1",
        "supercell_matrix": np.asarray(ph.supercell_matrix).tolist(),
        "unitcell_lattice_A": np.asarray(ph.unitcell.cell).tolist(),
        "unitcell_symbols": list(ph.unitcell.symbols),
        "unitcell_scaled_positions": np.asarray(ph.unitcell.scaled_positions).tolist(),
        "displaced_supercells": len(dataset),
        "displacements_A": [entry["displacement"].tolist() for entry in dataset],
        "force_constants_shape": list(np.asarray(ph.force_constants).shape),
        "q_path": plain_labels,
        "points_per_segment": 100,
        "frequency_unit": "meV",
        "VASP_to_THz": VASP_TO_THZ,
        "THz_to_meV": THZ_TO_MEV,
        "minimum_frequency_meV": float(frequencies_mev.min()),
        "maximum_frequency_meV": float(frequencies_mev.max()),
    }
    outputs[2].write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    for path in outputs:
        print(f"saved: {path}")


if __name__ == "__main__":
    main()
