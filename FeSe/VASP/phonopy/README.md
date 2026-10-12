# Phonopy｜FeSe 聲子、熱性質與主動學習

本目錄提供利用 GAP/QUIP 所得到的預測力進行聲子有限位移計算、與參考頻率比較及生成主動學習構型的範例。

| 程式／檔案 | 功能 |
| --- | --- |
| `QUIP_for_calc_phonon.py` | 從 Relaxed `CONTCAR` 與 GAP XML 計算有限位移力、力常數並儲存 Phonopy 結果 |
| `QUIP_calc_with_eigenvector.py` | 計算含 eigenvectors 的聲子色散，供後續模態分析 |
| `compare.py` | 在 Γ–X–M–Γ–Z–R–A–Z 路徑比較兩組 Phonopy 頻率 |
| `active_learning.py` | 依高對稱點聲子頻率差，選取模態並生成位移結構至 ASE database |
| `for_calc_some_use_thermal_properties.py` | 聲子 DOS、熱容、熵、Helmholtz 自由能 |
| `phonopy_disp.yaml` | 已提供的**位移資訊檔**，非完整 DFT band/force constants 參考 |

## 使用與驗證注意事項

1. 各腳本中的 GAP 模型路徑、結構檔、超胞大小可能不同；請先確認是否與同一模型及相同參考晶胞對應。
2. `compare.py` 需要具可讀取力常數的參考 Phonopy 檔（僅 `phonopy_disp.yaml` 不足），也需要相應的 MLIP 結果檔。
3. `active_learning.py` 假設比較資料具有對齊的 q-points 和聲子模態排列；如有交叉、簡併或不同模態排序，不能只依 branch index 直接認定是一一對應。
4. 高溫熱容接近 Dulong–Petit 極限，不足以單獨驗證 MLIP 預測的精度；還需實驗或 DFT 對照與誤差統計。
5. 有些腳本需要 `quippy`、`phonopy`、`ase`、`numpy`、`matplotlib`、`pyyaml`，並非單靠本 repo 就能在不同環境執行。

## 目前結果圖

參見 [根目錄 README](../../../README.md) 或 [FeSe/VASP/README.md](../README.md)。兩張圖均已由研究者確認使用 **74 筆訓練構型**，但尚未確認當時的模型檔與現有 440 筆 XYZ 之版本關係。圖中 **CSC = Charge-Self-Consistent（電荷自洽）**，不是 GAP 的縮寫；紅色 CSC 聲子曲線已確認是 **74 筆 CSC 總能量 → energy-only GAP → Phonopy** 的結果，條件為 **U=J=0**；因此它不是直接計算的 CSC 聲子，也不是有限 U、J 強關聯效應的驗證。
