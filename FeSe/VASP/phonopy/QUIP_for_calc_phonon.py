import numpy as np
from ase.io import read  # <--- 新增讀取功能
from phonopy import Phonopy
from phonopy.structure.atoms import PhonopyAtoms
from ase import Atoms
from ase.optimize import BFGS
from ase.filters import FrechetCellFilter
from quippy.potential import Potential
from ase.constraints import FixAtoms, FixCartesian


# --- 設定本次計算的 Supercell 大小 ---
# 針對 FeSe，建議先從 2x2x2 (N=2) 開始
# 如果是 N=2, K點建議 (5, 5, 3) (根據你之前的收斂測試)
N = 4
xml_filename = "GAP_final_try_4.xml"



# ==========================================
# 1. 讀取結構 (取代原本的 Step 1 Optimization)
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
    print(f"Error loading potential: {e}")
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
print(f"Relaxed Lattice:\n{atoms.get_cell()}")


# ==========================================
# 2. 設定 Phonopy 與 Supercell
# ==========================================
print(f"=== Step 2: Phonopy Setup (N={N}) ===")

unitcell = PhonopyAtoms(symbols=atoms.get_chemical_symbols(),
                        cell=atoms.get_cell(),
                        scaled_positions=atoms.get_scaled_positions())

phonon = Phonopy(unitcell,
                 supercell_matrix=[[N, 0, 0], [0, N, 0], [0, 0, N]])

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

phonon.forces = forces_set
phonon.produce_force_constants()
phonon.symmetrize_force_constants()
   
    
    # =========== [請在這裡加入存檔指令] ===========
print("Saving phonopy parameters to yaml...")
phonon.save(f"phonopy_params_N{N}44_QUIP_only_energy_final_try.yaml")
print(f"Saved: phonopy_params_N{N}44_QUIP_only_energy_final_try.yaml")
    # ============================================

