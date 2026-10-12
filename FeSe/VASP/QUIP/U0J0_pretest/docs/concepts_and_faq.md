# GAP → Phonopy｜觀念與常見問題（新手版）

返回 [FeSe U0J0 教學首頁](../README.md)。

## 1. DFT 能量、CSC、GAP、Phonopy 是不同工作

| 名稱 | 在這個範例中負責什麼 |
| --- | --- |
| DFT／DFT+gRISB | 產生參考晶體結構、參考能量；此 pre-test 為 U=J=0 |
| CSC（Charge Self-Consistent） | 參考電子結構計算的電荷自洽方式，**不是**另一套機器學習模型 |
| ASE | 產生／讀取原子結構、保存 XYZ，並將 GAP 接到原子力計算 |
| QUIP／GAP | 用參考能量訓練位能；預測能量與力 |
| Phonopy | 透過有限位移力計算力常數、聲子與振動熱力學性質 |

流程是「DFT 結構與能量 → extended XYZ → GAP → ASE 力 → Phonopy → 結果」。

## 2. Energy-only 不等於 Force-free

MLIP 學的是可微分的能量函數。對原子座標求負梯度可得到模型力，因此聲子計算使用的**是 GAP 預測的力**，並不是直接把單筆 total energy 丟進 Phonopy。

## 3. Extended XYZ 如何閱讀？

第一行是原子數，第二行是 metadata（晶格 `Lattice`、欄位格式 `Properties`、總能量 `energy`、週期邊界 `pbc`），後續每行是一顆原子的元素與座標。單位需與腳本的假設一致，這份資料的能量是**整個構型**的 eV。

## 4. 兩個資料集不能混用

- `U0J0_pretest/data/csc_data_74.xyz`：歷史 pre-test 使用，74 筆 32 原子紀錄、59 個不同幾何；檔案已原樣保存。
- `QUIP/energy_only_dataset.xyz`：另一個實驗的 440 筆 128 原子紀錄。
- 兩者超胞不同，GAP 設定也不同；重新跑 `QUIP/QUIP指令` 並不會得到這次 pre-test 的模型。

## 5. XML、SparseX 與 YAML 有什麼不同？

- **GAP XML**：訓練後的位能模型設定與參數入口。
- **SparseX**：在啟用分離存檔時，模型引用的稀疏環境資料；搬動 XML 時不能遺漏或任意改名。
- **Phonopy YAML**：可能存有結構、位移、力或力常數；**是否能直接重算頻譜需檢查內容**，不能只看副檔名。本例 `csc_ver.yaml` 含位移與 GAP forces，可重建力常數；`ground_truth.yaml` 需搭配 `phonon/reference_dft/FORCE_CONSTANTS`。

## 6. 最常見的錯誤

| 現象 | 先檢查 |
| --- | --- |
| `No module named quippy` | Python 環境中是否安裝了相容的 quippy |
| `gap_fit: command not found` | QUIP 訓練工具是否安裝或透過 HPC module 載入 |
| 讀模型時找不到 `sparseX` | XML 引用的全部 SparseX 是否同位置、檔名完全一致 |
| `FileNotFoundError: POSCAR/CONTCAR` | 執行目錄、路徑及該步驟使用的結構版本 |
| 計算出來的聲子與示範圖不同 | 是否混用 74/440 筆資料、不同 GAP XML、晶胞、supercell、q-path |
| 聲子有負（虛）頻 | 位能／力常數品質、平衡結構、位移距離、超胞與聲學和規則 |
| 熱容沒有接近高溫極限 | 單位、原子數正規化、模態與頻率範圍、溫度是否足夠高 |
| rattle 出現大量相同構型 | 隨機種子是否在每次迴圈重設；務必檢查結構重複 |
| XYZ 有能量卻不能重現訓練 | 檔案是否與 XML 內嵌命令所記錄的 `at_file` 真正對應 |
| `No module named f90wrap` | 已找到自建 quippy，但目前 Python 缺少該 QUIP binding 的執行依賴 |
| output 已存在而腳本停止 | 教學腳本預設禁止覆寫；改用新 output 目錄，保留上一輪結果 |

## 7. 做完後應該能解釋的差異

- **物理一致性**：例如高溫熱容的 3\(k_B\)/atom 極限，是檢查計算流程是否合理的一個線索。
- **定量準確度**：需要獨立資料、參考力或 DFT 聲子比較，才有能力說明預測誤差。
- **可重現性**：要有對應的 XYZ、訓練命令、完整 XML／SparseX、起始結構、Phonopy 設定與版本資訊，光有圖片不夠。

本資料夾的目標是**先學會完整操作，再逐步提高驗證標準**。
