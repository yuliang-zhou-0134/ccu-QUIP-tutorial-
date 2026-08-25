import numpy as np
import matplotlib.pyplot as plt
from ase import Atoms
from ase.build import bulk
from ase.optimize import BFGS
from phonopy import Phonopy
from phonopy.structure.atoms import PhonopyAtoms
from quippy.potential import Potential
from ase.io import read  
from ase.constraints import FixAtoms, FixCartesian


# ==========================================
# 設定區
# ==========================================
xml_filename = "GAP_sigma_0.0005_atom_sigma_0.46.xml "
N = 4  # Supercell 大小


# ==========================================
# 1. 結構設定 (固定晶格常數)
# ==========================================
print("=== Step 1: Loading Relaxed FeSe Structure ===")

# 直接讀取你已經優化好的 xyz 檔
# 務必確認你的 xyz 檔名正確
try:
    atoms = read('CONTCAR') 
    print(f"Structure loaded successfully: {atoms.get_chemical_formula()}")
    print(f"Lattice: {atoms.get_cell()}")
except Exception as e:
    print(f"Error loading file: {e}")
    exit()

try:
    calc_gap = Potential(param_filename=xml_filename)
except Exception as e:
    parprint(f"Error loading potential: {e}")
    exit()

atoms.calc = calc_gap

# 2. 【關鍵步驟】設定約束條件 (Constraints)
constraints = []

# 找出 Fe 和 Se 的原子索引 (Index)
# 假設你的 FeSe 結構裡只有這兩種原子
fe_indices = [atom.index for atom in atoms if atom.symbol == 'Fe']
se_indices = [atom.index for atom in atoms if atom.symbol == 'Se']

# (A) 把 Fe 完全鎖死 (FixAtoms)
# Fe 在層狀結構中通常是參考平面，不想讓它亂動
c_fe = FixAtoms(indices=fe_indices)
constraints.append(c_fe)

# (B) 讓 Se 只在 Z 軸移動 (FixCartesian)
# mask=[1, 1, 0] 代表: Fix X, Fix Y, Free Z
c_se = FixCartesian(se_indices, mask=[1, 1, 0])
constraints.append(c_se)

# 將約束條件套用到 atoms 物件上
atoms.set_constraint(constraints)

# 3. 開始幾何優化 (Relaxation)
# 注意：這裡直接把 atoms 丟進優化器，不要用 ExpCellFilter！
# 這樣晶格常數 (Cell) 就會被嚴格固定住。
opt = BFGS(atoms, logfile=None)
atoms.calc = calc_gap
print("開始優化 Se 高度...")
# fmax=0.0001 eV/A 是比較嚴格的標準，適合算聲子前使用
opt.run(fmax=0.000001)

# ==========================================
# 2. Phonopy 計算
# ==========================================
print(f"=== Step 2: Phonopy Calculation (N={N}) ===")

unitcell = PhonopyAtoms(symbols=atoms.get_chemical_symbols(),
                        cell=atoms.get_cell(),
                        scaled_positions=atoms.get_scaled_positions())

phonon = Phonopy(unitcell,
                 supercell_matrix=[[N, 0, 0], [0, N, 0], [0, 0, 2]])

phonon.generate_displacements(distance=0.01)
supercells = phonon.supercells_with_displacements

forces_set = []

# --- 計算基準力 ---
atoms_perfect = Atoms(symbols=phonon.supercell.symbols,
                      positions=phonon.supercell.positions,
                      cell=phonon.supercell.cell, pbc=True)
atoms_perfect.calc = calc_gap
f0 = atoms_perfect.get_forces()
print(f"Max background force (noise): {np.max(np.abs(f0)):.6f} eV/A")

# --- 計算位移力 ---
for i, sc in enumerate(supercells):
    if (i+1) % 10 == 0 or i == 0:
        print(f"Calculating displacement {i+1}/{len(supercells)}...")

    atoms_sc = Atoms(symbols=sc.symbols,
                     positions=sc.positions,
                     cell=sc.cell,
                     pbc=True)
    atoms_sc.calc = calc_gap
    f_disp = atoms_sc.get_forces()
    forces_set.append(f_disp - f0)

# ==========================================
# 3.save
# ==========================================
print("=== Step 3: Plotting (Manual Interpolation) ===")
phonon.forces = forces_set
phonon.produce_force_constants()
phonon.symmetrize_force_constants()

def get_linear_path(start, end, npoints):
    return [start + (end - start) * i / (npoints - 1) for i in range(npoints)]

G = np.array([0, 0, 0])
X = np.array([0.5, 0, 0.0])
M = np.array([0.5, 0.5, 0])
Z = np.array([0.0, 0.0, 0.5])
R = np.array([0.5, 0.0, 0.5])
A = np.array([0.5, 0.5, 0.5])

path1 = get_linear_path(G, X, 51)
path2 = get_linear_path(X, M, 51)
path3 = get_linear_path(M, G, 51)
path4 = get_linear_path(G, Z, 51)
path5 = get_linear_path(Z, R, 51)
path6 = get_linear_path(R, A, 51)
path7 = get_linear_path(A, Z, 51)

phonon.run_band_structure([path1, path2, path3, path4, path5, path6, path7],
        with_eigenvectors=True)


    
    # =========== [請在這裡加入存檔指令] ===========
print("Saving phonopy parameters to yaml...")
phonon.write_yaml_band_structure(filename="band_N444_energy.yaml")
print(f"Saved: band_N444_energy.yaml")
    # ============================================


