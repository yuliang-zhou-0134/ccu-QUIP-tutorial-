#!/usr/bin/env python3
# Si | MACE-MP-0 energy-only Stage Two -> Phono3py lattice thermal conductivity
# 用途：重現已執行過的 Si Phono3py 熱導率；不是 MACE 訓練程式。
# 在 Colab 先安裝：%pip install mace-torch ase phonopy phono3py
# 並先執行：from google.colab import drive; drive.mount('/content/drive')

from datetime import datetime
from pathlib import Path
import hashlib
import json

import matplotlib.pyplot as plt
import numpy as np
import torch
import ase
import phono3py as phono3py_module
from ase import Atoms
from ase.build import bulk
from ase.filters import FrechetCellFilter
from ase.optimize import BFGS
from mace.calculators import MACECalculator
from phono3py import Phono3py
from phonopy.structure.atoms import PhonopyAtoms

# ================== A. 只需要改這裡 ==================
ROOT = Path('/content/drive/MyDrive/xyz_for_training')
MODEL = ROOT / 'checkpoints/Si_MACE_only_energy_r_max5_TRUE_BLIND_run-123_stagetwo.model'
FC3_SUPERCELL = 2                  # 2x2x2 conventional = 64 Si atoms，與舊實驗一致
MESHES = (11, 15, 19)             # 先比較 300 K；19^3 可能比 11^3 慢不少
DISPLACEMENT_ANGSTROM = 0.03      # 沿用原 Cell 16 設定
TEMPERATURES = np.arange(100, 1001, 100, dtype=float)
# =====================================================

assert MODEL.is_file(), f'模型不存在：{MODEL}'
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
MODEL_SHA256 = hashlib.sha256(MODEL.read_bytes()).hexdigest()
OUT = ROOT / 'Si_thermal_results' / datetime.now().strftime('run_%Y%m%d_%H%M%S')
OUT.mkdir(parents=True, exist_ok=False)  # 每次產生新目錄，不覆寫先前的結果

print('MACE:', MODEL.name)
print('SHA256:', MODEL_SHA256)
print('Device:', DEVICE)
print('Output:', OUT)
calc = MACECalculator(model_paths=str(MODEL), device=DEVICE, default_dtype='float64')

# 1. 在這份 MACE 下重新弛豫結構；不要硬填舊的 5.587 Å
#    先用 primitive Si（2 atoms）弛豫，再建成對稱的 8-atom conventional cell。
prim = bulk('Si', 'diamond', a=5.43)
prim.calc = calc
opt = BFGS(FrechetCellFilter(prim), logfile=None)
converged = opt.run(fmax=1e-5, steps=200)
if not converged:
    raise RuntimeError('晶胞弛豫尚未達到 fmax=1e-5，停止計算。')

# diamond primitive volume = conventional volume / 4
a_cubic = float((4.0 * prim.get_volume()) ** (1.0 / 3.0))
atoms = bulk('Si', 'diamond', a=a_cubic, cubic=True)
atoms.calc = calc
max_force = float(np.abs(atoms.get_forces()).max())
max_stress = float(np.abs(atoms.get_stress()).max())
print(f'Relaxed conventional cubic a = {a_cubic:.8f} Å')
print(f'Ideal-cell |F|max = {max_force:.3g} eV/Å; |stress|max = {max_stress:.3g} eV/Å³')
if max_stress > 1e-3:
    raise RuntimeError('還原為 cubic cell 後殘餘 stress 偏大，請檢查晶格弛豫。')

# 2. 用和原本一樣的 conventional cell、fcc primitive matrix 執行 fc2/fc3
unitcell = PhonopyAtoms(
    symbols=atoms.get_chemical_symbols(),
    cell=atoms.cell.array,
    scaled_positions=atoms.get_scaled_positions(),
)
fcc_primitive = [[0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]]
ph3 = Phono3py(
    unitcell=unitcell,
    supercell_matrix=[FC3_SUPERCELL] * 3,
    primitive_matrix=fcc_primitive,
)
ph3.generate_displacements(distance=DISPLACEMENT_ANGSTROM)
supercells = ph3.supercells_with_displacements
print(f'{FC3_SUPERCELL}x{FC3_SUPERCELL}x{FC3_SUPERCELL} conventional supercell; '
      f'{len(supercells)} displaced configurations')
forces = []
for i, sc in enumerate(supercells, 1):
    if sc is None:
        raise RuntimeError(f'第 {i} 個 displacement 是 None；請檢查 cutoff 設定。')
    a = Atoms(symbols=sc.symbols, positions=sc.positions, cell=sc.cell, pbc=True)
    a.calc = calc
    f = a.get_forces()
    if not np.isfinite(f).all():
        raise ValueError(f'第 {i} 個 displacement 有 NaN/Inf forces。')
    forces.append(f)
    if i % 10 == 0 or i == len(supercells):
        print(f'MACE forces: {i}/{len(supercells)}')
ph3.forces = forces

print('產生 fc2 / fc3 ...')
ph3.produce_fc2()
ph3.symmetrize_fc2()
ph3.produce_fc3()
ph3.symmetrize_fc3()

# YAML 包含 displacement、forces 及 fc2/fc3，可在未來不重新呼叫 MACE。
ph3.save(str(OUT / 'phono3py_params_with_fc.yaml'),
         settings={'force_constants': True})

# 3. 固定 fc2/fc3，先只測 300 K q-mesh convergence
#    RTA，無 isotope / boundary scattering；與原 Notebook 設定一致。
mesh_rows = []
for mesh in MESHES:
    print(f'Calculating 300 K: q-mesh {mesh}x{mesh}x{mesh} ...')
    ph3.mesh_numbers = [mesh] * 3
    ph3.init_phph_interaction()
    ph3.run_thermal_conductivity(
        temperatures=[300.0], is_LBTE=False, is_isotope=False, write_kappa=False
    )
    K = np.asarray(ph3.thermal_conductivity.kappa, dtype=float)
    if K.ndim != 3 or K.shape[1] != 1 or K.shape[2] < 3:
        raise RuntimeError(f'Unexpected conductivity shape: {K.shape}')
    kxyz = K[0, 0, :3]  # [sigma=0, temperature=300K, xx/yy/zz]
    kavg = float(np.mean(kxyz))
    if not np.isfinite(kxyz).all():
        raise RuntimeError('熱導率包含 NaN/Inf。')
    mesh_rows.append((mesh, *map(float, kxyz), kavg))
    print(f'  kxx={kxyz[0]:.4f}, kyy={kxyz[1]:.4f}, '
          f'kzz={kxyz[2]:.4f}, average={kavg:.4f} W/(m·K)')

np.savetxt(
    OUT / 'mesh_convergence_300K.csv', mesh_rows, delimiter=',',
    header='mesh,kappa_xx_W_mK,kappa_yy_W_mK,kappa_zz_W_mK,kappa_xyz_mean_W_mK',
    comments='', fmt='%.8f'
)
if len(mesh_rows) >= 2:
    last, prev = mesh_rows[-1][-1], mesh_rows[-2][-1]
    rel_change = abs(last - prev) / abs(last) * 100 if last != 0 else np.inf
    print(f'最後兩組 mesh 的 300 K κ 平均值變化：{rel_change:.2f}%')
    if rel_change > 5:
        print('注意：最後兩個 mesh 的差異仍 >5%；不可宣稱 q-mesh 已收斂。')

plt.figure(figsize=(7, 5))
plt.plot([x[0] for x in mesh_rows], [x[-1] for x in mesh_rows], 'o-')
plt.xlabel('q-mesh N (N × N × N)')
plt.ylabel('300 K lattice κ (W/(m·K))')
plt.title('Si | q-mesh sensitivity (RTA, fixed fc2/fc3)')
plt.grid(alpha=0.35)
plt.tight_layout()
plt.savefig(OUT / 'mesh_convergence_300K.png', dpi=250)
plt.show()

# 4. 使用最大 q-mesh 畫 100–1000 K（不再計算第二次位移 forces）
final_mesh = MESHES[-1]
ph3.mesh_numbers = [final_mesh] * 3
ph3.init_phph_interaction()
ph3.run_thermal_conductivity(
    temperatures=TEMPERATURES, is_LBTE=False, is_isotope=False, write_kappa=False
)
TC = ph3.thermal_conductivity
K = np.asarray(TC.kappa, dtype=float)
T = np.asarray(TC.temperatures, dtype=float)
if K.shape[1] != len(T):
    raise RuntimeError(f'Unexpected temperature/kappa shapes: {T.shape}, {K.shape}')
kxx, kyy, kzz = K[0, :, 0], K[0, :, 1], K[0, :, 2]
kmean = (kxx + kyy + kzz) / 3.0
np.savetxt(
    OUT / 'kappa_vs_temperature.csv', np.column_stack([T, kxx, kyy, kzz, kmean]),
    delimiter=',', header='T_K,kappa_xx_W_mK,kappa_yy_W_mK,kappa_zz_W_mK,kappa_xyz_mean_W_mK',
    comments='', fmt='%.8f'
)
plt.figure(figsize=(8, 5))
plt.plot(T, kmean, 'o-', label='κ = (κxx+κyy+κzz)/3')
plt.xlabel('Temperature (K)')
plt.ylabel('Lattice thermal conductivity (W/(m·K))')
plt.title(f'Si MACE-MP-0 | RTA, q-mesh {final_mesh}³, SC {FC3_SUPERCELL}³')
plt.grid(alpha=0.35)
plt.legend()
plt.tight_layout()
plt.savefig(OUT / 'kappa_vs_temperature.png', dpi=300)
plt.show()

metadata = {
    'model_file': str(MODEL), 'model_sha256': MODEL_SHA256,
    'device': DEVICE, 'dtype': 'float64',
    'relaxed_conventional_cubic_a_A': a_cubic,
    'ideal_cell_max_force_eV_A': max_force,
    'ideal_cell_max_stress_eV_A3': max_stress,
    'fc2_fc3_supercell_conventional': [FC3_SUPERCELL] * 3,
    'displacement_A': DISPLACEMENT_ANGSTROM,
    'num_displaced_structures': len(supercells),
    'q_meshes_300K': list(MESHES),
    'final_q_mesh': [final_mesh] * 3,
    'method': 'Phono3py single-mode RTA; three-phonon scattering only',
    'is_isotope': False, 'boundary_mfp': None,
    'phonon3py_version': getattr(phono3py_module, '__version__', 'unknown'),
    'torch_version': torch.__version__,
    'ase_version': ase.__version__,
    'note': 'Mesh sensitivity tested; supercell/displacement/LBTE convergence not established.'
}
(OUT / 'settings.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')

print('\n300 K mesh convergence:')
for m, xx, yy, zz, avg in mesh_rows:
    print(f'{m:>2}³  xx={xx:.3f}  yy={yy:.3f}  zz={zz:.3f}  mean={avg:.3f} W/(m·K)')
print('\nTemperature dependence (largest mesh):')
for t, val in zip(T, kmean):
    print(f'{t:>4.0f} K: {val:.3f} W/(m·K)')
print('\n結果已存至:', OUT)
