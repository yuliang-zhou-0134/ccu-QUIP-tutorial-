import os
import shutil
from ase.io import read, write
from ase.build import sort
# ==========================================================
# 讀取初始 POSCAR
# ==========================================================
print("正在讀取初始 POSCAR...")
atoms = read("POSCAR")
supercell = atoms.repeat((2, 2, 2))
supercell = sort(supercell)
#建立超胞 and 排序
print(f"成功建立超胞！總共有 {len(supercell)} 顆原子。")

# 清除 constraint
supercell.set_constraint()

# ==========================================================
# 找出上半部原子
# ==========================================================
z_coords = supercell.positions[:, 2]
z_mid = (z_coords.max() + z_coords.min()) / 2.0
top_layer_indices = [i for i, z in enumerate(z_coords) if z > z_mid]

# ==========================================================
# shear 位移 (Å)
# ==========================================================
displacements = [
    -0.05, -0.04, -0.03, -0.025,
    -0.02, -0.015, -0.01, -0.005,
     0.005, 0.01, 0.015, 0.02,
     0.025, 0.03, 0.04, 0.05
]

# ==========================================================
# 建立 shear 資料夾
# ==========================================================
parent_dir = "shear"
# 避免重跑覆寫 shear/disp_*/ 下既有的 POSCAR、INCAR 與 DFT 結果。
if os.path.lexists(parent_dir):
    raise FileExistsError(
        f"目標資料夾已存在：{parent_dir}/。請先選擇新的工作目錄，勿覆寫原始資料。"
    )
os.makedirs(parent_dir)

print(f"\n已建立資料夾 {parent_dir}/")

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
# 建立所有 shear 結構
# ==========================================================

for d in displacements:

    shear_atoms = supercell.copy()
    pos = shear_atoms.positions

    # 上層沿 x 方向平移
    for i in top_layer_indices:
        pos[i, 0] += d

    shear_atoms.set_positions(pos)

    disp_dir = os.path.join(parent_dir, f"disp_{d:.3f}")

    scf_dir = os.path.join(disp_dir, "scf")
    csc_dir = os.path.join(disp_dir, "csc")

    os.makedirs(scf_dir)
    os.makedirs(csc_dir)

    # ------------------------------------------------------
    # 寫入 POSCAR
    # ------------------------------------------------------
    write(os.path.join(scf_dir, "POSCAR"),
          shear_atoms,
          format="vasp",
          vasp5=True,
          direct=True)

    write(os.path.join(csc_dir, "POSCAR"),
          shear_atoms,
          format="vasp",
          vasp5=True,
          direct=True)

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

    print(f"完成 {disp_dir}")

print("\n🎉 所有 shear 結構建立完成！")
