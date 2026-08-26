from ase.io import read
from quippy.potential import Potential
import matplotlib.pyplot as plt
import numpy as np

# 1. 設定檔案
xyz_file = 'si_training_easy.xyz'
gap_xml = 'GAP_Si_Final.xml'

print("Loading GAP model...")
pot = Potential(param_filename=gap_xml)

print(f"Reading data from {xyz_file}...")
atoms_list = read(xyz_file, index=':') 

dft_energies, gap_energies = [], []
dft_forces, gap_forces = [], []
dft_stresses, gap_stresses = [], []

print("Calculating predictions...")
for i, at in enumerate(atoms_list):
    # --- DFT Data ---
    try:
        dft_e_total = at.get_potential_energy()
    except:
        dft_e_total = at.info['energy']
    dft_energies.append(dft_e_total / len(at)) # eV/atom

    try:
        dft_f = at.get_forces().flatten()
    except:
        dft_f = at.arrays['forces'].flatten()
    dft_forces.extend(dft_f)
    
    dft_s = None
    try:
        dft_s = at.get_stress().flatten()
    except:
        if 'stress' in at.info: dft_s = at.info['stress'].flatten()
        elif 'virial' in at.info: dft_s = at.info['virial'].flatten()
    
    if dft_s is not None:
        dft_stresses.extend(dft_s)

    # --- GAP Data ---
    at.set_calculator(pot)
    gap_e = at.get_potential_energy() / len(at)
    gap_f = at.get_forces().flatten()
    gap_energies.append(gap_e)
    gap_forces.extend(gap_f)
    
    if dft_s is not None:
        gap_s = at.get_stress().flatten()
        gap_stresses.extend(gap_s)

    if i % 50 == 0: print(f"Processed {i} frames...")

# ==========================================
# 4. 計算 RMSE (關鍵新增部分)
# ==========================================
def calc_rmse(true, pred):
    return np.sqrt(np.mean((np.array(true) - np.array(pred))**2))

rmse_e = calc_rmse(dft_energies, gap_energies) * 1000 # 轉成 meV
rmse_f = calc_rmse(dft_forces, gap_forces)
if len(dft_stresses) > 0:
    rmse_s = calc_rmse(dft_stresses, gap_stresses)
else:
    rmse_s = 0.0

print(f"RMSE Energy: {rmse_e:.2f} meV/atom")
print(f"RMSE Force:  {rmse_f:.3f} eV/A")
print(f"RMSE Stress: {rmse_s:.3f} eV/A^3")

# ==========================================
# 5. 畫圖 (標題加上 RMSE)
# ==========================================
# ==========================================
# 5. 畫圖 (高畫質版)
# ==========================================
# 修改這裡！增加 dpi 參數，讓圖表在螢幕上顯示時就清晰一點
fig, ax = plt.subplots(1, 3, figsize=(18, 5), dpi=150)

# Energy
# 修改這裡！s=5 (點變小), alpha=0.3 (變透明)
ax[0].scatter(dft_energies, gap_energies, alpha=0.3, c='b', s=5, label='Data')
min_e, max_e = min(dft_energies), max(dft_energies)
ax[0].plot([min_e, max_e], [min_e, max_e], 'k--', lw=1, label='Ideal')
ax[0].set_title(f"Energy\nRMSE = {rmse_e:.2f} meV/atom")
ax[0].set_xlabel("DFT (eV/atom)")
ax[0].set_ylabel("GAP (eV/atom)")
# (選用) 加上格線會看起來更專業
ax[0].grid(True, linestyle='--', alpha=0.6)

# Force
# 修改這裡！Force 點通常更多，可以更小更透: s=2, alpha=0.2
ax[1].scatter(dft_forces, gap_forces, alpha=0.2, c='r', s=2)
min_f, max_f = min(dft_forces), max(dft_forces)
ax[1].plot([min_f, max_f], [min_f, max_f], 'k--', lw=1)
ax[1].set_title(f"Forces\nRMSE = {rmse_f:.3f} eV/A")
ax[1].set_xlabel("DFT (eV/A)")
ax[1].set_ylabel("GAP (eV/A)")
ax[1].grid(True, linestyle='--', alpha=0.6)

# Stress
if len(dft_stresses) > 0:
    # 修改這裡！s=5, alpha=0.3
    ax[2].scatter(dft_stresses, gap_stresses, alpha=0.3, c='g', s=5)
    min_s, max_s = min(dft_stresses), max(dft_stresses)
    ax[2].plot([min_s, max_s], [min_s, max_s], 'k--', lw=1)
    ax[2].set_title(f"Virial Stress\nRMSE = {rmse_s:.3f} eV/A^3")
    ax[2].set_xlabel("DFT (eV/A^3)")
    ax[2].set_ylabel("GAP (eV/A^3)")
    ax[2].grid(True, linestyle='--', alpha=0.6)
else:
    ax[2].text(0.5, 0.5, "No Stress Data Found", ha='center')

plt.tight_layout()

# ==========================================
# 關鍵修改！加上 dpi=300
# ==========================================
output_filename = "validation_plots_v3_high_res.png"
# 存成 PNG (高解析度)
plt.savefig(output_filename, dpi=300)

# (進階選用) 如果你想存成向量圖(無限放大不失真)，可以取消下面這行的註解，存成 PDF
# plt.savefig("validation_plots_v3.pdf")

print(f"✅ 高畫質圖檔已儲存為 {output_filename}")
# plt.show() # 如果在伺服器上跑，建議註解掉這行
