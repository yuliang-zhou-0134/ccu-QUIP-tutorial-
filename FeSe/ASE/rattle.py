import os
import shutil
from ase.io import read, write
from ase.build import sort

# ==========================================================
# 參數設定
# ==========================================================
num_samples = 50
displacement_stdev = 0.04  # Å

print("正在讀取初始 POSCAR...")

# 建立 2×2×2 超胞並排序
atoms = read("POSCAR")
supercell = atoms.repeat((2, 2, 2))
supercell = sort(supercell)

print(f"成功建立超胞！總共有 {len(supercell)} 顆原子。")

# 清除 constraint
supercell.set_constraint()

# ==========================================================
# 要複製的檔案
# ==========================================================

# SCF
scf_files = [
    ("INCAR_scf", "INCAR"),
    ("POTCAR", "POTCAR"),
    ("KPOINTS", "KPOINTS"),
]

# CSC
csc_files = [
    ("INCAR_csc", "INCAR"),
    ("main.py", "main.py"),
    ("STOPCAR", "STOPCAR"),
    ("grisb_config.toml", "grisb_config.toml"),
    ("link_files.sh", "link_files.sh"),
    ("autorm.sh", "autorm.sh"),
    ("plo.cfg", "plo.cfg"),
    ("run.sh", "run.sh"),
]

# ==========================================================
# 建立所有 rattle 結構
# ==========================================================

for i in range(1, num_samples + 1):

    atoms_new = supercell.copy()

    # 加入隨機位移
    atoms_new.rattle(stdev=displacement_stdev)

    task_dir = f"task_{i:03d}"
    scf_dir = os.path.join(task_dir, "scf")
    csc_dir = os.path.join(task_dir, "csc")

    os.makedirs(scf_dir, exist_ok=True)
    os.makedirs(csc_dir, exist_ok=True)

    # ------------------------------------------------------
    # 寫入 POSCAR
    # ------------------------------------------------------
    write(
        os.path.join(scf_dir, "POSCAR"),
        atoms_new,
        format="vasp",
        vasp5=True,
        direct=True,
    )

    write(
        os.path.join(csc_dir, "POSCAR"),
        atoms_new,
        format="vasp",
        vasp5=True,
        direct=True,
    )

    # ------------------------------------------------------
    # SCF 檔案
    # ------------------------------------------------------
    for src, dst in scf_files:
        if os.path.exists(src):
            shutil.copy(src, os.path.join(scf_dir, dst))
        else:
            print(f"⚠ 找不到 {src}")

    # ------------------------------------------------------
    # CSC 檔案
    # ------------------------------------------------------
    for src, dst in csc_files:
        if os.path.exists(src):
            shutil.copy(src, os.path.join(csc_dir, dst))
        else:
            print(f"⚠ 找不到 {src}")

    print(f"完成 {task_dir}")

print("\n🎉 所有 rattle 結構建立完成！")
