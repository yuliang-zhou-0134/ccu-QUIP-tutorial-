import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from phonopy import load

# ==========================================
# 1. 設定檔案
# ==========================================
files_info = [
    ('VASP', 'phonopy_disp.yaml', 'blue', '--'),
    ('QUIP',   'phonopy_params_N444_QUIP_only_energy_final_no_fix.yaml',   'red',  '-')
]

# ==========================================
# 2. 輔助函式
# ==========================================
def get_linear_path(start, end, npoints):
    return [start + (end - start) * i / (npoints - 1) for i in range(npoints)]

def get_band_data(filename):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found!")
        return None
    try:
        print(f"Processing {filename}...")
        phonon = load(filename)
        
        G = np.array([0, 0, 0])
        X = np.array([0.5, 0, 0.0])
        M = np.array([0.5, 0.5, 0])
        Z = np.array([0.0, 0.0, 0.5])
        R = np.array([0.5, 0.0, 0.5])
        A = np.array([0.5, 0.5, 0.5])
        
        path1 = get_linear_path(G, X, 100)
        path2 = get_linear_path(X, M, 100)
        path3 = get_linear_path(M, G, 100)
        path4 = get_linear_path(G, Z, 100)
        path5 = get_linear_path(Z, R, 100)
        path6 = get_linear_path(R, A, 100)
        path7 = get_linear_path(A, Z, 100)
        
        phonon.run_band_structure([path1, path2, path3, path4, path5, path6, path7])
        bands_dict = phonon.get_band_structure_dict()
        frequencies = bands_dict['frequencies']
        full_bands = np.concatenate(frequencies, axis=0)
        return full_bands * 4.135667696  #THz to meV
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None

# ==========================================
# 3. 讀取與繪圖
# ==========================================
data_list = []
for label, fname, color, style in files_info:
    d = get_band_data(fname)
    if d is not None:
        data_list.append({'label': label, 'data': d, 'color': color, 'style': style})

if len(data_list) < 2:
    print("Need both files to compare!")
    sys.exit()

# 畫圖 (上下兩張)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=True, 
                               gridspec_kw={'height_ratios': [3, 1]})
plt.subplots_adjust(hspace=0.05) 

# 取出數據
gpaw_data = data_list[0]['data']
qe_data = data_list[1]['data']
x_axis = np.arange(gpaw_data.shape[0])

# --- 上圖：能帶疊加 ---
for entry in data_list:
    d = entry['data']
    for i in range(d.shape[1]):
        lbl = entry['label'] if i == 0 else None
        ax1.plot(x_axis, d[:, i], color=entry['color'], linestyle=entry['style'], 
                 linewidth=2, label=lbl, alpha=0.8)

# --- 下圖：QUIP - VASP 差異 ---
if gpaw_data.shape == qe_data.shape:
    diff = qe_data - gpaw_data
    max_diff = np.max(np.abs(diff))
    print(f"\n=== Result: Max Difference between QUIP and VASP (N=4) ===")
    print(f"Max Diff = {max_diff:.4f} meV")
    
    for i in range(diff.shape[1]):
        lbl = "QUIP - VASP" if i == 0 else None
        ax2.plot(x_axis, diff[:, i], color='black', linewidth=1.5)

ax2.axhline(0, color='gray', linestyle=':', alpha=0.5)

# --- 美化 ---
TITLE_SIZE = 28
LABEL_SIZE = 24
TICK_SIZE = 20
LEGEND_SIZE = 18

special_points = [0, 100, 200, 300, 400, 500, 600 ,700]
special_labels = [r'$\Gamma$', 'X', 'M', r'$\Gamma$', 'Z', 'R', 'A', 'Z']

ax1.set_title('VASP vs QUIP (Finite Displacement N=4)', fontsize=TITLE_SIZE,pad=15)
ax1.set_ylabel('Energy (meV)', fontsize=LABEL_SIZE)
ax1.tick_params(axis='y', labelsize=TICK_SIZE)
ax1.legend(loc='lower left' , bbox_to_anchor=(0.12, 0.04),framealpha=0.9, fontsize=LEGEND_SIZE)
ax1.grid(True, linestyle='--', alpha=0.3)
ax1.set_xlim(0, 700)

ax2.set_ylabel(r'$\Delta \omega$ (QUIP - VASP)', fontsize=LABEL_SIZE)
ax2.set_xticks(special_points)
ax2.set_xticklabels(special_labels, fontsize=TICK_SIZE)
ax2.tick_params(axis='y', labelsize=TICK_SIZE)
ax2.grid(True, linestyle='--', alpha=0.3)

for p in special_points:
    ax1.axvline(x=p, color='gray', linestyle=':', linewidth=2, alpha=0.5)
    ax2.axvline(x=p, color='gray', linestyle=':', linewidth=2, alpha=0.5)

plt.savefig('comparison_QUIP_vs_GPAW_N4_only_energy.png', dpi=600)
print("Plot saved to comparison_QUIP_vs_GPAW_N4_only_energy.png")
plt.show()
