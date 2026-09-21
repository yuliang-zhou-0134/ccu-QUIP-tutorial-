python3 - <<'PY'
import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# =========================================================
# 1. User settings
# =========================================================
ROOT = Path("/home/yuliang/fese_THL/vasp/U3J0.3/0%/csc_task4_checkpoint")

# 選擇要畫哪個版本：
# "MGammaXM"  -> M-Γ-X-M
# "full"      -> Γ-X-M-Γ-Z-R-A-Z
MODE = "MGammaXM"

# 正式論文用字體/尺寸（適合雙欄 paper）
FIG_W = 7.0          # inches; 雙欄較合適
FIG_H = 3.6
DPI = 400

TITLE_FS = 10.5
LABEL_FS = 10
TICK_FS = 9
CBAR_FS = 9
LEGEND_FS = 8

DFT_LINEWIDTH = 0.75
DFT_LINECOLOR = "white"
DFT_LINEALPHA = 0.85

OMEGA_MIN = -3.0
OMEGA_MAX =  3.0
VMAX_PERCENTILE = 99.5

# =========================================================
# 2. Input files
# =========================================================
RESULTS_DIR = ROOT / "run" / "task4_production_25" / "results"
KPATH_DIR   = ROOT / "run" / "task4_production_25" / "kpath"

MODE_CONFIG = {
    "MGammaXM": {
        "npz": RESULTS_DIR / "Akomega_MGammaXM.npz",
        "title": r"DFT bands overlaid on the calculated spectral function $A(k,\omega)$ along M-$\Gamma$-X-M",
        "tick_indices": [0, 40, 80, 120],
        "tick_labels": ["M", r"$\Gamma$", "X", "M"],
        "out_png": RESULTS_DIR / "Akomega_MGammaXM_overlay.png",
        "out_pdf": RESULTS_DIR / "Akomega_MGammaXM_overlay.pdf",
    },
    "full": {
        "npz": RESULTS_DIR / "Akomega_full.npz",
        "title": r"DFT bands overlaid on the calculated spectral function $A(k,\omega)$ along $\Gamma$-X-M-$\Gamma$-Z-R-A-Z",
        "tick_indices": [0, 40, 80, 120, 160, 200, 240, 280],
        "tick_labels": [r"$\Gamma$", "X", "M", r"$\Gamma$", "Z", "R", "A", "Z"],
        "out_png": RESULTS_DIR / "Akomega_full_overlay.png",
        "out_pdf": RESULTS_DIR / "Akomega_full_overlay.pdf",
    }
}

cfg = MODE_CONFIG[MODE]
npz_path = cfg["npz"]
eigenval_path = KPATH_DIR / "EIGENVAL"
outcar_path = KPATH_DIR / "OUTCAR"

# =========================================================
# 3. Plot style (formal / publication-like)
# =========================================================
plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "mathtext.fontset": "dejavuserif",
    "font.size": TICK_FS,
    "axes.titlesize": TITLE_FS,
    "axes.labelsize": LABEL_FS,
    "xtick.labelsize": TICK_FS,
    "ytick.labelsize": TICK_FS,
    "legend.fontsize": LEGEND_FS,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "axes.linewidth": 0.8,
})

# =========================================================
# 4. Helpers
# =========================================================
def read_fermi_from_outcar(path):
    text = path.read_text(errors="ignore")
    matches = re.findall(r"E-fermi\s*:\s*([\-0-9.]+)", text)
    if not matches:
        raise RuntimeError(f"Cannot find E-fermi in {path}")
    return float(matches[-1])

def read_eigenval(path):
    """
    Parse VASP EIGENVAL.
    Returns:
        kpoints: (nkpts, 3)
        eigvals: (nkpts, nbands)
    """
    lines = path.read_text(errors="ignore").splitlines()

    if len(lines) < 7:
        raise RuntimeError(f"{path} looks too short to be a valid EIGENVAL")

    # Standard VASP EIGENVAL format:
    # line 6 (index 5) -> nelect nkpts nbands
    header = lines[5].split()
    if len(header) < 3:
        raise RuntimeError("Failed to parse nkpts/nbands from EIGENVAL line 6")

    nelect, nkpts, nbands = map(int, header[:3])

    kpoints = np.zeros((nkpts, 3), dtype=float)
    eigvals = np.zeros((nkpts, nbands), dtype=float)

    i = 6
    ik = 0

    while ik < nkpts and i < len(lines):
        # skip blank lines
        while i < len(lines) and not lines[i].strip():
            i += 1

        if i >= len(lines):
            break

        # k-point line: kx ky kz weight
        parts = lines[i].split()
        if len(parts) < 4:
            raise RuntimeError(f"Unexpected k-point line in EIGENVAL: {lines[i]}")
        kpoints[ik] = [float(parts[0]), float(parts[1]), float(parts[2])]
        i += 1

        # band lines: band_index eigenvalue occupation
        for ib in range(nbands):
            parts = lines[i].split()
            if len(parts) < 2:
                raise RuntimeError(f"Unexpected band line in EIGENVAL: {lines[i]}")
            eigvals[ik, ib] = float(parts[1])
            i += 1

        ik += 1

    if ik != nkpts:
        raise RuntimeError(f"Parsed only {ik}/{nkpts} k-points from EIGENVAL")

    return kpoints, eigvals

# =========================================================
# 5. Load spectral data
# =========================================================
d = np.load(npz_path)
omega = d["omega_ev"]
kdist = d["path_distance_reciprocal_angstrom"]
Akw   = d["spectral_weight"]
src_idx = d["source_full_path_indices"]

# =========================================================
# 6. Load DFT band data
# =========================================================
kpts_all, eig_all = read_eigenval(eigenval_path)
efermi = read_fermi_from_outcar(outcar_path)

# KPATH calculation includes the anchor as the first point.
# Spectral NPZ is built from the physical path only, so drop anchor first.
kpts_path = kpts_all[1:, :]
eig_path = eig_all[1:, :] - efermi   # shift to E_F = 0

# source_full_path_indices may be 1-based or 0-based depending on export
src_idx = np.asarray(src_idx, dtype=int)

if src_idx.min() >= 1 and src_idx.max() <= len(eig_path):
    sel = src_idx - 1
elif src_idx.min() >= 0 and src_idx.max() < len(eig_path):
    sel = src_idx
else:
    raise RuntimeError(
        f"source_full_path_indices out of range: min={src_idx.min()}, max={src_idx.max()}, "
        f"while eig_path has {len(eig_path)} points"
    )

eig_sel = eig_path[sel, :]    # shape = (n_path_points, nbands)

# only plot bands that enter the energy window
band_mask = np.any(
    (eig_sel >= OMEGA_MIN - 0.3) & (eig_sel <= OMEGA_MAX + 0.3),
    axis=0
)
eig_plot = eig_sel[:, band_mask]

# =========================================================
# 7. Plot
# =========================================================
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

vmax = np.percentile(Akw, VMAX_PERCENTILE)

mesh = ax.pcolormesh(
    kdist,
    omega,
    Akw.T,
    shading="auto",
    cmap="magma",
    vmax=vmax,
    rasterized=True,
)

# overlay DFT bands
for ib in range(eig_plot.shape[1]):
    ax.plot(
        kdist,
        eig_plot[:, ib],
        color=DFT_LINECOLOR,
        lw=DFT_LINEWIDTH,
        alpha=DFT_LINEALPHA,
    )

# high symmetry vertical lines
tick_positions = [kdist[i] for i in cfg["tick_indices"]]
for x in tick_positions:
    ax.axvline(x, color="white", lw=0.6, alpha=0.28)

# Fermi level
ax.axhline(0.0, color="white", lw=0.8, ls="--", alpha=0.75)

# labels / title
ax.set_title(cfg["title"], pad=6)
ax.set_xlabel("k-path distance")
ax.set_ylabel(r"Energy relative to $E_F$ (eV)")

ax.set_xticks(tick_positions)
ax.set_xticklabels(cfg["tick_labels"])

ax.set_xlim(kdist.min(), kdist.max())
ax.set_ylim(OMEGA_MIN, OMEGA_MAX)

cbar = fig.colorbar(mesh, ax=ax, pad=0.02)
cbar.set_label(r"Spectral weight $A(k,\omega)$", fontsize=CBAR_FS)
cbar.ax.tick_params(labelsize=TICK_FS)

fig.tight_layout(pad=0.8)

# save
fig.savefig(cfg["out_png"], bbox_inches="tight")
fig.savefig(cfg["out_pdf"], bbox_inches="tight")
plt.close(fig)

print(f"MODE           = {MODE}")
print(f"E-fermi used   = {efermi:.6f} eV (from {outcar_path.name})")
print(f"Input NPZ      = {npz_path}")
print(f"Input EIGENVAL = {eigenval_path}")
print(f"Saved PNG      = {cfg['out_png']}")
print(f"Saved PDF      = {cfg['out_pdf']}")
PY
