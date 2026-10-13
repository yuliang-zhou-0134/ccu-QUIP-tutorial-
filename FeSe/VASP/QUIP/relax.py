import os
import glob
import re
import numpy as np
import matplotlib.pyplot as plt
from ase.io import read, write
from quippy.potential import Potential
from ase.optimize import BFGS
from ase.filters import FrechetCellFilter

# ==========================================
# 0. 設定模型與通用參數
# ==========================================
GAP_XML = "test_phonon/GAP_average_method_angle_3b.xml"  # 請替換為你的模型參數檔
pot = Potential("IP GAP", param_filename=GAP_XML)
pot.name_ = 'GAP'           # 修補 ASE 與 QUIP 軌跡寫入的相容性問題


# ==========================================
# 全晶胞弛豫 (Relaxation)
# ==========================================
print("--- 開始進行全晶胞弛豫 ---")

relax_target = "POSCAR" 

if os.path.exists(relax_target):
    # 舊研究腳本預設不覆寫已保存的結構、軌跡與最佳化紀錄。
    existing_outputs = [
        name for name in ("CONTCAR", "opt.traj", "opt.log") if os.path.lexists(name)
    ]
    if existing_outputs:
        raise FileExistsError(
            "已有弛豫輸出：" + ", ".join(existing_outputs)
            + "；請換用新的工作目錄，避免覆寫既有計算。"
        )
    atoms = read(relax_target, format="vasp")
    atoms.calc = pot

    ecf = FrechetCellFilter(atoms)
    opt = BFGS(ecf, trajectory='opt.traj', logfile='opt.log')
    opt.run(fmax=0.0001)

    sc_a, sc_b, sc_c = atoms.cell.lengths()
    sc_vol = atoms.get_volume()
    sc_energy = atoms.get_potential_energy()

    uc_a = sc_a / 2.0
    uc_b = sc_b / 2.0
    uc_c = sc_c / 2.0

    print("\n" + "="*45)
    print("              最終最佳化結果")
    print("="*45)
    print(f"總系統最低能量  : {sc_energy:.4f} eV")
    print(f"超晶胞總體積    : {sc_vol:.4f} A^3")
    print("-" * 45)
    print("【2x2x2 超晶胞 (Supercell) 晶格常數】")
    print(f"  a = {sc_a:.5f} A")
    print(f"  b = {sc_b:.5f} A")
    print(f"  c = {sc_c:.5f} A")
    print("-" * 45)
    print("【單位晶格 (Unit Cell) 晶格常數】")
    print(f"  a = {uc_a:.5f} A")
    print(f"  b = {uc_b:.5f} A")
    print(f"  c = {uc_c:.5f} A")
    print("="*45 + "\n")
    write("CONTCAR", atoms, format="vasp")
else:
    print(f"-> [錯誤] 當前目錄下找不到用於弛豫的 {relax_target} 檔案。")
