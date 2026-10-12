import os
import shutil
import numpy as np
from phonopy import Phonopy
from phonopy.interface.calculator import read_crystal_structure, write_crystal_structure

def main():
    # 1. 定義要分配的附錄檔案列表
    scf_files = ["POTCAR", "KPOINTS"]
    csc_files = ["main.py", "STOPCAR", "grisb_config.toml", "link_files.sh", "autorm.sh", "plo.cfg", "run.sh"]
    
    # 檢查必要檔案是否存在，給予提示
    required_files = ["POSCAR", "INCAR_scf", "INCAR_csc"] + scf_files + csc_files
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"⚠️ 警告：找不到以下檔案，這可能會導致後續計算報錯：\n{', '.join(missing_files)}\n")

    # 2. 讀取未經位移的原胞 POSCAR
    try:
        unitcell, _ = read_crystal_structure("POSCAR", interface_mode='vasp')
    except FileNotFoundError:
        print("❌ 錯誤：找不到原胞 POSCAR 檔案，程式中止。")
        return

    # 3. 設定 2x2x2 超胞矩陣
    supercell_matrix = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]

    # 4. 產生位移的等差數列 (0.005 到 0.035, 公差 0.005)
    # 使用 np.round 避免浮點數產生如 0.0150000001 的誤差
    amplitudes = np.round(np.arange(0.005, 0.040, 0.005), 3)

    task_counter = 1

    print("開始生成位移結構與資料夾...")
    
    for amp in amplitudes:
        # 實例化 Phonopy
        phonon = Phonopy(unitcell, supercell_matrix)
        
        # 產生位移：is_plusminus=True 會同時產生 + 與 - 兩個方向的對稱位移
        phonon.generate_displacements(distance=amp, is_plusminus=True)
        supercells = phonon.supercells_with_displacements
        
        for sc in supercells:
            # 跳過沒有位移的完美超胞 (通常是列表中的 None 或是完全沒變的結構)
            if sc is None:
                continue
            
            # 建立 task 資料夾，例如 task_001_disp_0.005
            task_dir = f"task_{task_counter:03d}_disp_{amp:.3f}"
            os.makedirs(task_dir, exist_ok=True)
            
            # 將生成的超胞寫入 task 資料夾並命名為 POSCAR
            task_poscar_path = os.path.join(task_dir, "POSCAR")
            write_crystal_structure(task_poscar_path, sc, interface_mode='vasp')
            
            # 建立 scf 與 csc 子資料夾
            scf_dir = os.path.join(task_dir, "scf")
            csc_dir = os.path.join(task_dir, "csc")
            os.makedirs(scf_dir, exist_ok=True)
            os.makedirs(csc_dir, exist_ok=True)
            
            # (補充) 為了讓 VASP/gRISB 可以在 scf 與 csc 內順利執行，將 POSCAR 一併複製到子資料夾內
            shutil.copy(task_poscar_path, os.path.join(scf_dir, "POSCAR"))
            shutil.copy(task_poscar_path, os.path.join(csc_dir, "POSCAR"))
            
            # --- 處理 scf 資料夾 ---
            if os.path.exists("INCAR_scf"):
                shutil.copy("INCAR_scf", os.path.join(scf_dir, "INCAR"))
            for f in scf_files:
                if os.path.exists(f):
                    shutil.copy(f, os.path.join(scf_dir, f))
                    
            # --- 處理 csc 資料夾 ---
            if os.path.exists("INCAR_csc"):
                shutil.copy("INCAR_csc", os.path.join(csc_dir, "INCAR"))
            for f in csc_files:
                if os.path.exists(f):
                    shutil.copy(f, os.path.join(csc_dir, f))
                    
            task_counter += 1

    print(f"✅ 腳本執行完畢！共生成了 {task_counter - 1} 個 task 資料夾。")

if __name__ == "__main__":
    main()
