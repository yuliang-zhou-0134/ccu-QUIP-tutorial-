import numpy as np
import yaml
import phonopy
from ase import Atoms
from ase.db import connect
from phonopy.structure.atoms import PhonopyAtoms

# ================= 設定區 =================
DFT_YAML = "band.yaml"    # DFT 算的 band.yaml (Ground Truth)
ML_YAML = "band_N444_energy.yaml"      # ML 預測的 band.yaml (用來比對誤差)
PHONOPY_PARAMS = "phonopy_params_N444_QUIP_only_energy_sigma_0.0005_atom_sigma_0.46_for_plot.yaml" # 必須包含結構資訊與 Force Constants 或 Eigenvectors
DB_NAME = "active_learning_v3.db" # 輸出的資料庫檔名

SUPERCELL_DIM = [4, 4, 2]     # 指定生成 4x4x2 超胞
ERROR_THRESHOLD = 0.5        # 誤差門檻 (THz),~16.7cm^-1
TOP_N_MODES = 50               # 挑選誤差最大的前 N 個模式
AMPLITUDE_RANGE = 0.08        # 位移最大幅度 (Angstrom),for Z try to add more amp
NUM_SAMPLES = 30               # 每個模式生成的樣本數 (線性內插),for Z use more data

# ==========================================

def get_bands_data(filename):
    """讀取 yaml 檔中的頻率數據"""
    print(f"Reading {filename}...")
    with open(filename, 'r') as f:
        data = yaml.safe_load(f)
    
    # 解析 q-points 和 frequencies
    # 結構通常是: phonon -> [ {q-position: ..., band: [{frequency: ...}, ...]}, ... ]
    q_points = []
    frequencies = []
    
    for pt in data['phonon']:
        q = pt['q-position']
        freqs = [b['frequency'] for b in pt['band']]
        q_points.append(q)
        frequencies.append(freqs)
        
    return np.array(q_points), np.array(frequencies)

def find_high_error_modes(dft_freqs, ml_freqs, q_points):
    """
    找出誤差最大的模式，但只鎖定 Q 點分量為 0.0 或 0.5 的高對稱點。
    (例如 Gamma, M, X, Z, R, A)
    """
    diff = np.abs(dft_freqs - ml_freqs)
    
    error_list = []
    n_q, n_band = diff.shape
    
    print(f"正在篩選高對稱點 (只保留 0.0 或 0.5)...")
    
    for i in range(n_q):
        # === 新增篩選邏輯 Start ===
        q = q_points[i]
        
        # 檢查每一個分量 (qx, qy, qz) 是否都接近 0.0 或 0.5
        # 容許誤差 1e-4，避免浮點數精確度問題
        is_high_sym = True
        for val in q:
            # 取絕對值，確保 -0.5 也被視為 0.5
            abs_val = abs(val)
            # 如果它既不是 0.0 也不是 0.5，就由它去吧 (False)
            if not (abs_val < 1e-4 or abs(abs_val - 0.5) < 1e-4):
                is_high_sym = False
                break
        
        if not is_high_sym:
            continue # 如果不是我們要的點，直接跳過換下一個
        # === 新增篩選邏輯 End ===

        for j in range(n_band):
            err = diff[i, j]
            # 這裡可以加入虛頻懲罰 (Optional): 如果 ML < -0.1, err *= 10
            if ml_freqs[i, j] < -0.01:
                err *= 100.0

            if err > ERROR_THRESHOLD:
                error_list.append({
                    'error': err,
                    'q_idx': i,
                    'band_idx': j,
                    'q_point': q_points[i],
                    'freq_dft': dft_freqs[i, j],
                    'freq_ml': ml_freqs[i, j]
                })
    
    # 根據誤差大小排序 (由大到小)
    error_list.sort(key=lambda x: x['error'], reverse=True)
    
    # 這裡只回傳前 N 個，但因為我們已經過濾了雜訊，
    # 這裡選出來的一定是 Gamma, M, A 這些「正牌」的高對稱點
    return error_list[:TOP_N_MODES]

def phonopy_to_ase(ph_atoms):
    """將 PhonopyAtoms 轉換為 ASE Atoms"""
    return Atoms(symbols=ph_atoms.symbols,
                 positions=ph_atoms.positions,
                 cell=ph_atoms.cell,
                 pbc=True)

def main():
    # 1. 讀取頻率數據
    q_dft, freq_dft = get_bands_data(DFT_YAML)
    q_ml, freq_ml = get_bands_data(ML_YAML)
    
    if freq_dft.shape != freq_ml.shape:
        print("錯誤: DFT 和 ML 的 q-point 路徑或能帶數不一致，無法比較！")
        return

    # 2. 找出誤差最大的模式
    target_modes = find_high_error_modes(freq_dft, freq_ml, q_dft)

    # === 新增：去除重複的模式 ===
    unique_modes = []
    seen = set()

    print(f"\n正在去除重複的模式...")
    for m in target_modes:
        # 將 numpy array 轉成 tuple 方便比對 (取小數點後4位避免誤差)
        q_tuple = tuple(np.round(m['q_point'], 4))
        band = m['band_idx']
        
        identifier = (q_tuple, band)
        
        if identifier not in seen:
            seen.add(identifier)
            unique_modes.append(m)
        else:
            print(f"跳過重複模式: Q={m['q_point']}, Band={band}")

    target_modes = unique_modes
    # ==========================
    
    print(f"\n=== 最終篩選出 {len(target_modes)} 個不重複的高誤差模式 ===")
    # ... (接續原本的程式碼)
    if not target_modes:
        print(f"沒有發現誤差 > {ERROR_THRESHOLD} cm^-1 的模式。")
        return

    print(f"\n=== 篩選出 {len(target_modes)} 個高誤差模式 ===")
    for idx, m in enumerate(target_modes):
        print(f"Rank {idx+1}: Q={m['q_point']}, Band={m['band_idx']}, Err={m['error']:.2f}, DFT={m['freq_dft']:.2f}, ML={m['freq_ml']:.2f}")

    # 3. 載入 Phonopy 物件 (用來生成調變結構)
    # 注意: 這裡讀取的 params 必須包含 eigenvectors，或者你要在這裡重新計算
    print(f"\nLoading Phonopy parameters from {PHONOPY_PARAMS}...")
    ph = phonopy.load(PHONOPY_PARAMS)
    
    # 確保使用指定的超胞大小
    # 注意: Modulation 功能是基於原始 Unit Cell 擴充到指定的 Dimension
    
    # 準備寫入 DB
    db = connect(DB_NAME)
    count = 0
    
    # 設定內插係數: 從 -0.02 到 +0.02 分成 7 份
    # 例如: [-0.02, -0.0133, -0.0067, 0.0, 0.0067, 0.0133, 0.02]
    amplitudes = np.linspace(-AMPLITUDE_RANGE, AMPLITUDE_RANGE, NUM_SAMPLES)
    
    blacklist = []
    

    blacklist = amplitudes[np.abs(amplitudes) <= 0.04]     #set amplitude <= 0.04  not calc 
    tolerance = 1e-5

    print("\n=== 開始生成結構並寫入資料庫 ===")
    
    total_structures = 0
    
    for mode_info in target_modes:
        q_pt = mode_info['q_point']
        band_idx = mode_info['band_idx']
        
        print(f"Processing Mode: Q={q_pt}, Band={band_idx}")
        
        for amp in amplitudes:
            # --- [FILTERING LOGIC] ---
            # Check if amp is in blacklist
            skip = False
            for bad_val in blacklist:
                if abs(amp - bad_val) < tolerance:
                    skip = True
                    break
            
            if skip:
                # print(f"  -> Skipping amplitude {amp:.4f} (Already exists)")
                continue
            # 設定 Modulation
            # phonon_modes = [[q_point, band_index, amplitude, phase]]
            # amplitude 設為 1.0，然後我們用 argument 的 amplitude 去縮放，
            # 但 Phonopy 的 set_modulations 的 amplitude 參數定義比較特別 (它是縮放因子)
            # 為了精確控制 Å，通常需要正規化。
            # 這裡我們簡化處理：直接將 amp 傳入，假設 Phonopy 的 eigenvector 是 normalized 的
            
            phonon_modes = [[q_pt, band_idx, 1.0, 0]] 
            ph.run_modulations(dimension=SUPERCELL_DIM, phonon_modes=phonon_modes)
            mod_cell = ph.get_modulated_supercells()[0]
            
            # ==========================================
            # 🔧 [關鍵修正] 強制縮放位移量 (Manual Scaling)
            # ==========================================
            
            # 1. [生成基準] 振幅為 0 的完美超胞 (Reference)
            ph.run_modulations(dimension=SUPERCELL_DIM, 
                               phonon_modes=[[q_pt, band_idx, 0.0, 0]])
            perfect_cell = ph.get_modulated_supercells()[0]
            
            # 2. [生成方向] 振幅為 1.0 的結構 (Direction)
            ph.run_modulations(dimension=SUPERCELL_DIM, 
                               phonon_modes=[[q_pt, band_idx, 1.0, 0]])
            mod_cell = ph.get_modulated_supercells()[0]

            # 3. [計算] 
            pos_perfect = perfect_cell.positions
            pos_mod = mod_cell.positions
            diff_vector = pos_mod - pos_perfect
            current_max_disp = np.max(np.linalg.norm(diff_vector, axis=1))
            
            # 4. [決定縮放比例]
            scaling_factor = 0.0
            if current_max_disp > 1e-9:
                scaling_factor = amp / current_max_disp
            
            # 5. [算出新座標]
            new_positions = pos_perfect + (diff_vector * scaling_factor)

            # ==========================================
            # 🛑 關鍵檢查 (Debug Print)
            # ==========================================
            # 算出實際位移量，印出來給你確認
            real_max_disp = np.max(np.linalg.norm(new_positions - pos_perfect, axis=1))
            print(f"  Target Amp: {amp:.4f} | Scaling Factor: {scaling_factor:.2f} | Real Disp: {real_max_disp:.6f}")
            
            if real_max_disp < 1e-4 and abs(amp) > 1e-4:
                print("  ❌ 警告：位移放大失敗！請檢查程式碼！")
            # ==========================================

            # 6. [直接創建 ASE Atoms] - 避開 Phonopy 物件轉換的地雷
            # 我們直接用 "new_positions" 來建立 ASE 物件，保證座標是對的
            ase_atoms = Atoms(symbols=perfect_cell.symbols,
                              positions=new_positions,
                              cell=perfect_cell.cell,
                              pbc=True)
            
            # 7. [寫入資料庫]
            # 加入 Metadata
            info_data = {
                "type": "active_learning_gen",
                "q_point": str(q_pt),
                "band_index": int(band_idx),
                "displacement_amp": float(amp),
                "error_val": float(mode_info['error']),
                "original_freq_dft": float(mode_info['freq_dft']),
                "real_max_displacement": float(real_max_disp) # 順便存起來以防萬一
            }
            
            db.write(ase_atoms, key_value_pairs=info_data)
            count += 1

    print(f"\n成功！共生成 {count} 個結構，已存入 {DB_NAME}")
if __name__ == "__main__":
    main()
