import os
import shutil
from ase.io import read, write

# --- 參數設定 ---
input_poscar = 'POSCAR_4*4*2_perfect'  # 你的原始擴胞 POSCAR
base_dir = "mlip_training_set_v2"         # 統一存放在這個主目錄下
vasp_inputs = ['INCAR', 'KPOINTS', 'POTCAR']  # 僅複製工作目錄中實際存在的輸入檔
displacement_stdev = 0.01              # Rattle 微擾大小

# 讀取原始結構
atoms_origin = read(input_poscar, format='vasp')

# 設定要測試的應變比例 (+- 3%) for v2(v1 is strain +-2%)
strains = [0.97 ,0.972 , 0.974, 0.976, 0.978, 1.022, 1.024, 1.026, 1.028, 1.03]

# 在寫入任何檔案前，先檢查全部預定輸出，避免重跑覆寫 VASP 結果。
task_names = [f"{kind}_{s:.3f}" for kind in ("vol_strain", "z_strain") for s in strains]
existing_tasks = [
    os.path.join(base_dir, name) for name in task_names
    if os.path.lexists(os.path.join(base_dir, name))
]
if existing_tasks:
    raise FileExistsError(
        f"已有 {len(existing_tasks)} 個目標任務（例如 {existing_tasks[0]}）；"
        "請換用新的輸出目錄，不要覆寫既有計算。"
    )
os.makedirs(base_dir, exist_ok=True)

# ==========================================
# 1. 生成體積應變 (Volumetric Strain)
# ==========================================
print("開始生成 Volumetric Strain 結構...")
for s in strains:
    folder_name = f"vol_strain_{s:.3f}"
    task_path = os.path.join(base_dir, folder_name)
    os.makedirs(task_path)
    
    atoms = atoms_origin.copy()
    
    # 施加等比例體積應變 (X, Y, Z 同時縮放)
    cell = atoms.get_cell() * s
    atoms.set_cell(cell, scale_atoms=True)
    
    # 加入微擾
    atoms.rattle(stdev=displacement_stdev, seed=100 + int(s * 1000))
    
    write(os.path.join(task_path, 'POSCAR'), atoms, format='vasp', direct=True)
    
    for f in vasp_inputs:
        if os.path.exists(f):
            shutil.copy(f, task_path)

# ==========================================
# 2. 生成 Z 軸單軸應變 (Z-Strain)
# ==========================================
print("開始生成 Z-Strain 結構...")
for s in strains:
    folder_name = f"z_strain_{s:.3f}"
    task_path = os.path.join(base_dir, folder_name)
    os.makedirs(task_path)
    
    atoms = atoms_origin.copy()
    
    # 只針對 Z 方向 (c 軸，也就是第 3 個晶格向量) 進行縮放
    cell = atoms.get_cell()
    cell[2] = cell[2] * s  
    atoms.set_cell(cell, scale_atoms=True)
    
    # 加入微擾 (換一個 seed 基準避免跟體積應變的隨機擾動重複)
    atoms.rattle(stdev=displacement_stdev, seed=200 + int(s * 1000))
    
    write(os.path.join(task_path, 'POSCAR'), atoms, format='vasp', direct=True)
    
#    for f in vasp_inputs:
#        if os.path.exists(f):
#            shutil.copy(f, task_path)

print(f"🎉 完成！已在 {base_dir} 資料夾下生成了 {len(strains)*2} 個計算任務。")
