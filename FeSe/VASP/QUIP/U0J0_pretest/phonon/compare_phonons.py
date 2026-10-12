#!/usr/bin/env python3
"""Compare reproduced GAP and reference DFT finite-displacement phonons."""

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
VASP_TO_THZ = 15.633302
THZ_TO_MEV = 4.135667696
PATH_LABELS = ["Gamma", "X", "M", "Gamma", "Z", "R", "A", "Z"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gap-yaml",
        type=Path,
        default=ROOT
        / "phonon"
        / "output_reproduction_4x4"
        / "csc_ver_reproduced_4x4.yaml",
    )
    parser.add_argument(
        "--historical-gap-yaml", type=Path, default=ROOT / "phonon" / "csc_ver.yaml"
    )
    parser.add_argument(
        "--dft-yaml", type=Path, default=ROOT / "phonon" / "ground_truth.yaml"
    )
    parser.add_argument(
        "--dft-force-constants",
        type=Path,
        default=ROOT / "phonon" / "reference_dft" / "FORCE_CONSTANTS",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "phonon" / "output_dft_gap_comparison",
    )
    return parser.parse_args()


def paths() -> list[np.ndarray]:
    gamma = np.array([0.0, 0.0, 0.0])
    x = np.array([0.5, 0.0, 0.0])
    m = np.array([0.5, 0.5, 0.0])
    z = np.array([0.0, 0.0, 0.5])
    r = np.array([0.5, 0.0, 0.5])
    a = np.array([0.5, 0.5, 0.5])
    nodes = [gamma, x, m, gamma, z, r, a, z]
    return [np.linspace(start, end, 100) for start, end in zip(nodes, nodes[1:])]


def frequencies(ph) -> tuple[np.ndarray, np.ndarray]:
    expected = paths()
    ph.unit_conversion_factor = VASP_TO_THZ
    ph.run_band_structure(expected)
    band = ph.get_band_structure_dict()
    actual_qpoints = [np.asarray(segment) for segment in band["qpoints"]]
    if len(actual_qpoints) != len(expected) or any(
        not np.array_equal(actual, wanted)
        for actual, wanted in zip(actual_qpoints, expected)
    ):
        raise SystemExit("error: returned q-points differ from requested q-path")
    qpoints = np.concatenate(actual_qpoints, axis=0)
    frequencies_mev = np.concatenate(band["frequencies"], axis=0) * THZ_TO_MEV
    return qpoints, frequencies_mev


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    plot_out = output_dir / "dft_gap_phonon_comparison.png"
    data_out = output_dir / "dft_gap_bands_meV.npz"
    metrics_out = output_dir / "comparison_metrics.json"
    outputs = [plot_out, data_out, metrics_out]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise SystemExit("error: refusing to overwrite:\n  " + "\n  ".join(existing))
    output_dir.mkdir(parents=True, exist_ok=True)

    gap = load(args.gap_yaml.resolve(), produce_fc=True)
    old_gap = load(args.historical_gap_yaml.resolve(), produce_fc=True)
    dft = load(
        args.dft_yaml.resolve(),
        force_constants_filename=args.dft_force_constants.resolve(),
        produce_fc=True,
    )
    for label, ph in (("GAP", gap), ("historical GAP", old_gap), ("DFT", dft)):
        if ph.force_constants is None or not np.isfinite(ph.force_constants).all():
            raise SystemExit(f"error: {label} force constants are missing or non-finite")

    gap_matrix = np.asarray(gap.supercell_matrix, dtype=int)
    dft_matrix = np.asarray(dft.supercell_matrix, dtype=int)
    if not np.array_equal(gap_matrix, np.diag([4, 4, 4])) or not np.array_equal(
        dft_matrix, gap_matrix
    ):
        raise SystemExit("error: GAP and DFT are not both 4x4x4 supercells")
    if gap.unitcell.symbols != dft.unitcell.symbols:
        raise SystemExit("error: GAP and DFT unit-cell species/order differ")

    gap_qpoints, gap_frequencies = frequencies(gap)
    dft_qpoints, dft_frequencies = frequencies(dft)
    old_qpoints, old_gap_frequencies = frequencies(old_gap)
    if not np.array_equal(gap_qpoints, dft_qpoints) or not np.array_equal(
        gap_qpoints, old_qpoints
    ):
        raise SystemExit("error: GAP, historical GAP, and DFT q-points differ")
    if gap_frequencies.shape != dft_frequencies.shape:
        raise SystemExit(
            f"error: incompatible branches: GAP={gap_frequencies.shape}, "
            f"DFT={dft_frequencies.shape}"
        )

    difference = gap_frequencies - dft_frequencies
    flat_index = int(np.argmax(np.abs(difference)))
    q_index, branch_index = np.unravel_index(flat_index, difference.shape)
    lattice_difference = np.asarray(gap.unitcell.cell) - np.asarray(dft.unitcell.cell)
    position_difference = (
        np.asarray(gap.unitcell.scaled_positions)
        - np.asarray(dft.unitcell.scaled_positions)
    )
    position_difference -= np.rint(position_difference)
    historical_gap_difference = gap_frequencies - old_gap_frequencies
    metrics = {
        "runtime_phonopy_version": phonopy.__version__,
        "q_path": PATH_LABELS,
        "points_per_segment": 100,
        "qpoints_identical": True,
        "band_array_shape": list(gap_frequencies.shape),
        "branches": int(gap_frequencies.shape[1]),
        "frequency_unit": "meV",
        "gap_supercell_matrix": gap_matrix.tolist(),
        "dft_supercell_matrix": dft_matrix.tolist(),
        "species_and_order_identical": True,
        "gap_lattice_A": np.asarray(gap.unitcell.cell).tolist(),
        "dft_lattice_A": np.asarray(dft.unitcell.cell).tolist(),
        "maximum_abs_lattice_component_difference_A": float(
            np.abs(lattice_difference).max()
        ),
        "maximum_abs_wrapped_fractional_position_difference": float(
            np.abs(position_difference).max()
        ),
        "direct_sorted_branch_MAE_meV": float(np.mean(np.abs(difference))),
        "direct_sorted_branch_RMSE_meV": float(np.sqrt(np.mean(difference**2))),
        "direct_sorted_branch_max_abs_difference_meV": float(
            np.abs(difference).max()
        ),
        "max_difference_qpoint_index": int(q_index),
        "max_difference_qpoint_reduced": gap_qpoints[q_index].tolist(),
        "max_difference_branch_zero_based": int(branch_index),
        "max_difference_signed_GAP_minus_DFT_meV": float(
            difference[q_index, branch_index]
        ),
        "reproduced_vs_historical_GAP_max_abs_difference_meV": float(
            np.abs(historical_gap_difference).max()
        ),
        "comparison_limitation": (
            "Branches are compared by ascending frequency index at each q-point; "
            "degenerate modes and crossings are not matched by eigenvector overlap."
        ),
        "historical_figure_raw_data_available": False,
    }
    metrics_out.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    np.savez_compressed(
        data_out,
        qpoints_reduced=gap_qpoints,
        gap_frequencies_meV=gap_frequencies,
        dft_frequencies_meV=dft_frequencies,
        gap_minus_dft_meV=difference,
    )

    segment_x = np.concatenate([np.linspace(i, i + 1, 100) for i in range(7)])
    figure, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(9, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )
    for branch in range(gap_frequencies.shape[1]):
        top.plot(
            segment_x,
            dft_frequencies[:, branch],
            color="#2446ff",
            linestyle="--",
            linewidth=1.4,
            label="DFT" if branch == 0 else None,
        )
        top.plot(
            segment_x,
            gap_frequencies[:, branch],
            color="#ff2020",
            linewidth=1.4,
            label="GAP" if branch == 0 else None,
        )
        bottom.plot(segment_x, difference[:, branch], color="black", linewidth=0.9)

    labels = [r"$\Gamma$", "X", "M", r"$\Gamma$", "Z", "R", "A", "Z"]
    for axis in (top, bottom):
        for boundary in range(8):
            axis.axvline(boundary, color="0.75", linestyle=":", linewidth=0.8)
        axis.grid(axis="y", color="0.88", linestyle="--", linewidth=0.6)
    top.axhline(0.0, color="0.45", linewidth=0.7)
    bottom.axhline(0.0, color="0.45", linewidth=0.7)
    top.set_ylabel("Frequency (meV)")
    top.set_title("FeSe DFT vs reproduced GAP phonons (4x4x4)")
    top.legend(frameon=False)
    bottom.set_ylabel(r"$\omega_{GAP}-\omega_{DFT}$ (meV)")
    bottom.set_xticks(range(8), labels)
    bottom.set_xlim(0, 7)
    figure.tight_layout()
    figure.savefig(plot_out, dpi=300)
    plt.close(figure)
    print(json.dumps(metrics, indent=2))
    print(f"saved outputs in: {output_dir}")


if __name__ == "__main__":
    main()
