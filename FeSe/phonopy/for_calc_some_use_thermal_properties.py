import numpy as np
import matplotlib.pyplot as plt
from ase.io import read
from phonopy import Phonopy
from phonopy.structure.atoms import PhonopyAtoms
from quippy.potential import Potential

# ================= 設定區域 =================
input_structure_file = '../CONTCAR'
potential_string = 'GAP_final_try_4.xml'
supercell_matrix = [[4, 0, 0], [0, 4, 0], [0, 0, 4]]

# 溫度設定 (K)
t_min = 0
t_max = 1000
t_step = 10

# ================= 繪圖風格設定 (針對大專生計畫優化) =================
# 使用類似學術期刊的風格
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
plt.rcParams['mathtext.fontset'] = 'stix' # 讓數學符號更好看
plt.rcParams['axes.linewidth'] = 1.5      # 座標軸線條加粗
plt.rcParams['xtick.major.width'] = 1.5   # 刻度加粗
plt.rcParams['ytick.major.width'] = 1.5
plt.rcParams['xtick.direction'] = 'in'    # 刻度朝內 (物理期刊常見習慣)
plt.rcParams['ytick.direction'] = 'in'
plt.rcParams['font.size'] = 12            # 全局字體大小

# ===================================================================

def ase_to_phonopy(ase_atoms):
    return PhonopyAtoms(symbols=ase_atoms.get_chemical_symbols(),
                        scaled_positions=ase_atoms.get_scaled_positions(),
                        cell=ase_atoms.cell)

def main():
    # --- 1. 載入結構並初始化 Phonopy ---
    unitcell_ase = read(input_structure_file)
    unitcell_phonopy = ase_to_phonopy(unitcell_ase)
    
    phonon = Phonopy(unitcell_phonopy,
                     supercell_matrix=supercell_matrix)
    
    # 生成位移 (0.01 Angstrom 是預設值，可調整)
    phonon.generate_displacements(distance=0.01)
    supercells = phonon.supercells_with_displacements
    
    # --- 2. 使用 Quippy 計算受力 ---
    # 初始化 Quippy Potential
    calc = Potential(param_filename=potential_string)
    
    print(f"開始計算受力，共有 {len(supercells)} 個位移結構...")
    
    force_sets = []
    for i, sc_phonopy in enumerate(supercells):
        # 將 Phonopy supercell 轉回 ASE atoms 以進行計算
        # 注意：PhonopyAtoms 沒有直接轉 ASE 的方法，需手動重建
        sc_ase = read(input_structure_file) # 這裡只是一個 dummy，需重新設定 cell 和 positions
        # 更嚴謹的做法是建立一個全新的 ASE atoms
        from ase import Atoms
        sc_ase = Atoms(symbols=sc_phonopy.symbols,
                       scaled_positions=sc_phonopy.scaled_positions,
                       cell=sc_phonopy.cell,
                       pbc=True)
        
        # 設定 calculator 並計算力
        sc_ase.calc = calc
        forces = sc_ase.get_forces()
        force_sets.append(forces)
        print(f"  - 結構 {i+1}/{len(supercells)} 計算完成")

    # --- 3. 設定受力並計算力常數 ---
    phonon.forces = force_sets
    phonon.produce_force_constants()
    
    # --- 4. 計算 DOS (Density of States) ---
    # 設定 mesh (例如 20x20x20)，數值越大越精細
    mesh = [30, 30, 30]
    phonon.run_mesh(mesh, is_mesh_symmetry=False)
    phonon.run_total_dos()
    total_dos_dict = phonon.get_total_dos_dict()
    
    frequencies = total_dos_dict['frequency_points']
    dos_values = total_dos_dict['total_dos']
    
    # --- 5. 計算熱力學性質 (Entropy, Free Energy, Cv) ---
    phonon.run_thermal_properties(t_step=t_step,
                                  t_max=t_max,
                                  t_min=t_min)
    tp_dict = phonon.get_thermal_properties_dict()
    
    # 取出數據
    total_dos_dict = phonon.get_total_dos_dict()
    frequencies = total_dos_dict['frequency_points']
    dos_values = total_dos_dict['total_dos']
    
    tp_dict = phonon.get_thermal_properties_dict()
    temps = tp_dict['temperatures']
    free_energy = tp_dict['free_energy']
    entropy = tp_dict['entropy']
    heat_capacity = tp_dict['heat_capacity'] # 這裡就是你要的 Heat Capacity (Cv)

    

    # ================= 繪圖區域 (Dulong-Petit 驗證版) =================
    print("=== Step 3: Plotting (Verification: 3R Limit) ===")
    
    # 1. 物理常數與原子數設定
    R = 8.31446  # 氣體常數 J/K/mol
    
    # 這裡自動抓取你的 unitcell 原子數 (如果你用 cubic=True，這裡會是 8)
    n_atoms = len(unitcell_phonopy) 
    print(f"Detected number of atoms in unit cell: {n_atoms}")
    
    # 2. 數據轉換
    # THz -> meV
    THZ_TO_INV_CM = 4.136
    frequencies_cm = frequencies * THZ_TO_INV_CM
    
    # Heat Capacity 正規化：換算成 "每顆原子有幾個 kB" (無因次，或單位為 kB)
    # 公式: Cv_per_atom_in_kB = Cv_total / (n_atoms * R)
    # 理論上高溫極限應該趨近於 3
    cv_per_atom_kB = heat_capacity / (n_atoms * R)

    # 字體與排版設定 (維持之前漂亮的比例)
    SIZE_TITLE = 11
    SIZE_LABEL = 9
    SIZE_TICK  = 8
    
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['DejaVu Serif', 'Liberation Serif', 'serif'],
        'mathtext.fontset': 'stix',
        'axes.linewidth': 1.0,
        'xtick.major.width': 0.8,
        'ytick.major.width': 0.8,
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'xtick.labelsize': SIZE_TICK,
        'ytick.labelsize': SIZE_TICK
    })

    fig, axes = plt.subplots(2, 2, figsize=(10, 6), dpi=300, constrained_layout=True)
    line_style = {'linewidth': 1.5, 'color': '#1f77b4'}

    # --- (a) Phonon DOS ---
    ax = axes[0, 0]
    ax.plot(frequencies_cm, dos_values, 'k-', linewidth=1.0)
    ax.fill_between(frequencies_cm, dos_values, color='silver', alpha=0.5)
    ax.set_xlabel('Frequency (meV)', fontsize=SIZE_LABEL)
    ax.set_ylabel('DOS', fontsize=SIZE_LABEL)
    ax.set_title('(a) Phonon DOS', fontsize=SIZE_TITLE, loc='left', fontweight='bold')
    ax.set_xlim(0, max(frequencies_cm)*1.05)
    ax.set_ylim(bottom=0)
    
    # --- (b) Heat Capacity (重點修改！) ---
    ax = axes[0, 1]
    # 畫出數據
    ax.plot(temps, cv_per_atom_kB, **line_style, label='Calculated')
    
    # 畫出 3R 極限線 (Dulong-Petit limit)
    ax.axhline(y=3, color='r', linestyle='--', linewidth=1.0, label='Dulong-Petit (3$k_B$)')
    
    ax.set_xlabel('Temperature (K)', fontsize=SIZE_LABEL)
    # Y軸標籤改為 k_B/atom
    ax.set_ylabel('$C_v$ ($k_B$/atom)', fontsize=SIZE_LABEL)
    ax.set_title('(b) Heat Capacity', fontsize=SIZE_TITLE, loc='left', fontweight='bold')
    ax.set_xlim(0, t_max)
    ax.set_ylim(0, 3.5) # 設定範圍讓 3 位於上方舒適的位置
    ax.legend(fontsize=7, loc='lower right', frameon=False) # 加個圖例

    # --- (c) Entropy ---
    ax = axes[1, 0]
    ax.plot(temps, entropy, **line_style)
    ax.set_xlabel('Temperature (K)', fontsize=SIZE_LABEL)
    ax.set_ylabel('Entropy (J/K/mol)', fontsize=SIZE_LABEL)
    ax.set_title('(c) Entropy', fontsize=SIZE_TITLE, loc='left', fontweight='bold')
    ax.set_xlim(0, t_max)
    ax.set_ylim(bottom=0)

    # --- (d) Helmholtz Free Energy ---
    ax = axes[1, 1]
    ax.plot(temps, free_energy, **line_style)
    ax.set_xlabel('Temperature (K)', fontsize=SIZE_LABEL)
    ax.set_ylabel('Free Energy (kJ/mol)', fontsize=SIZE_LABEL)
    ax.set_title('(d) Helmholtz Free Energy', fontsize=SIZE_TITLE, loc='left', fontweight='bold')
    ax.set_xlim(0, t_max)
    
    plt.show()
    filename = 'phonon_thermodynamics_3R.png'
    plt.savefig(filename, dpi=300)
    print(f"圖表已生成: {filename}")

if __name__ == "__main__":
    main()
