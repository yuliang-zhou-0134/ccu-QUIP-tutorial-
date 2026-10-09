# FeSe U=J=0｜從 energy-only GAP 到 Phonopy 的入門實作

> **教學文件建置中（PR 草稿）**：本教學的原始 74 筆 XYZ、模型 XML／SparseX、Phonopy 結果與腳本仍需從實驗室伺服器補入並實測。本頁會清楚區分「已確認的歷史結果」與「目前可以實際操作的步驟」。在檔案補齊前，請勿將此資料夾當成可一鍵執行的完整範例。

## 這份教學要讓你學會什麼？

完成後，你應能自己說明並執行：

1. **參考能量**：從 DFT／DFT+gRISB 計算取得結構與總能量，存成 extended XYZ。
2. **模型訓練**：用 QUIP 的 `gap_fit` 訓練只以能量監督的 Gaussian Approximation Potential（GAP）。
3. **力與聲子**：GAP 能量對原子座標求導，給出預測力；Phonopy 透過有限位移力求力常數與聲子頻率。
4. **檢查結果**：繪出聲子色散、聲子 DOS、熱容、熵與振動自由能，並知道哪些現象算合理、哪些尚不能證明精度。

**建議學習順序：先用現成模型重現結果 → 再自己訓練 GAP → 最後自己從 VASP 產生新資料。** 前兩關不應強制要求你先會跑 VASP 或 gRISB。

### 核心觀念：只用能量訓練，為什麼可以算聲子？

訓練資料只有各構型的總能量 `energy`，不直接提供 DFT 的力或應力標記。GAP 建立可微分的能量模型

\[
E_{\mathrm{GAP}}(\mathbf R_1,\ldots,\mathbf R_N),\qquad
\mathbf F_i=-\nabla_{\mathbf R_i}E_{\mathrm{GAP}}.
\]

Phonopy 會產生小幅位移構型，向 GAP 查詢各構型的力，再以有限差分估算力常數（能量對位移的二階導數），建構動力矩陣並計算聲子。因此 **energy-only 指的是訓練標記，不是聲子計算完全不使用力**。

## 這次示範用的是哪一組資料？

- 材料：FeSe；每筆訓練結構為 **32 原子（Fe16Se16）**。
- 參考標記：**CSC（charge-self-consistent）計算所得的能量**，設定 **U=0、J=0**。
- 訓練檔：`csc_data.xyz` 共 **74 筆紀錄、59 個不同幾何構型**；其中 16 筆 rattle 記錄其實是同一個構型重複出現。
- 歷史模型：`csc_ver.xml` 及其引用的 9 個 SparseX 檔，採 **2-body + 3-body** 描述符，`default_sigma={0.002 0.0 0.0 0.0}`、`e0_method=average`。
- 產出：GAP + Phonopy 的聲子色散（與 DFT 參考比較）及 DOS、熱容、熵、自由能。

**不要混用** [上一層的 `energy_only_dataset.xyz`](../energy_only_dataset.xyz)：那是另一個 **440 筆、每筆 128 原子** 的資料集；[現有 `QUIP指令`](../QUIP指令) 使用 2-body + SOAP + 3-body，並非此處 74 筆 pre-test 的訓練設定。

## 預計的檔案結構與狀態

下列路徑是教學整理的**目標結構**，不代表檔案現已全部上傳。

```text
U0J0_pretest/
├── README.md                    # 你正在閱讀的教學
├── docs/
│   └── concepts_and_faq.md      # 基礎觀念、單位與常見錯誤
├── data/
│   └── csc_data_74.xyz          # 待補：實際用於歷史模型的原始 XYZ
├── training/
│   └── train_gap.sh             # 待補：由歷史 XML 的原始 gap_fit 指令還原
├── model/
│   ├── csc_ver.xml              # 待補：原始訓練模型
│   └── csc_ver.xml.sparseX.*    # 待補：XML 真正引用的 9 個檔案
├── phonon/
│   ├── POSCAR / CONTCAR         # 待確認實際起始與弛豫結構
│   ├── csc_ver.yaml             # 待補：歷史 Phonopy 結果
│   ├── relax.py                 # 待補、檢查可移植路徑
│   ├── plot_phonon.py           # 待補、檢查可移植路徑
│   └── thermal.py               # 待補、檢查可移植路徑
└── results/
    ├── phonon_comparison.png    # 待補：DFT 與 GAP 結果
    └── thermal_properties.png   # 待補：振動熱力學結果
```

若收錄 DFT/MLIP 比較圖，需另提供 `csc_vs_ground_truth.py` 與 `ground_truth.yaml` 才能重現比較，而不能只提供圖片。

## 第 0 關｜確認環境

建議在各自的 Python 虛擬環境執行；共享實驗室伺服器請遵守登入節點、運算節點和軟體模組的使用規範。

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy matplotlib ase phonopy pyyaml
python -c "import ase, phonopy, numpy; print('ASE/Phonopy/NumPy 匯入成功')"
```

還需要 **與 ASE 相容的 quippy** 才能讀取 GAP 模型，例如依環境選用 `quippy-ase` 套件；**`gap_fit` 是 QUIP 訓練工具，不會因安裝 Phonopy 就自動出現**。不同工作站／HPC 的編譯、MPI 與模組方式可能不同，請以實驗室的 QUIP 安裝說明為準。先檢查：

```bash
command -v gap_fit || echo "gap_fit 未在 PATH 中；需先安裝或載入 QUIP"
python -c "from quippy.potential import Potential; print('quippy 可用')"
```

如果缺少 `gap_fit`，可以先練習讀取與檢查 XYZ；若已有 `quippy` 和預訓練模型，亦可先走第一關。

## 第 1 關｜先觀察資料，使用既有模型重現結果

**本關需等待 `data/`、`model/`、`phonon/` 的必要檔案上傳及完成測試。**

切到本教學目錄後，先認識 extended XYZ：

```bash
cd FeSe/VASP/QUIP/U0J0_pretest
python - <<'PY'
from ase.io import read

frames = read("data/csc_data_74.xyz", index=":")
print("訓練紀錄數：", len(frames))
print("第一筆原子數：", len(frames[0]))
print("第一筆化學式：", frames[0].get_chemical_formula())
print("第一筆總能量 (eV)：", frames[0].get_potential_energy())
PY
```

**預期：** 74 筆紀錄，第一筆 32 原子，具有 Fe 和 Se，以及可讀取的能量。這個檢查不是評估 GAP 精度，只是確保資料格式正確。

了解第二行標頭的用途：

```text
32
Lattice="..." Properties=species:S:1:pos:R:3 energy=-... pbc="T T T"
Fe x y z
Se x y z
...
```

- `Lattice`：3×3 晶格向量（Å）。
- `Properties`：元素符號與三維原子座標。
- `energy`：該 **整個構型** 的總能量（eV），不是每原子能量。
- `pbc`：週期性邊界條件。

確認既有 GAP 模型所需 XML 與 SparseX 全部位於 `model/`，再進行模型讀取與 Phonopy 計算。**具體可執行的聲子重現指令，將在檔案補齊並由伺服器實測後加入**；不能直接套用上一層 `phonopy/QUIP_for_calc_phonon.py` 的模型名稱、`N=4` 或輸入晶胞。

完成後應能回答：GAP 在哪裡提供原子力？Phonopy 使用什麼晶胞與超胞？聲子頻率單位是 THz 還是 meV？

## 第 2 關｜用 74 筆能量重新訓練 GAP

**本關需等待 `training/train_gap.sh` 由原始 XML 的訓練命令還原、檢查並實測。不要直接執行上一層 440 筆資料的指令。**

預期流程：

1. 先備份既有 XML，新的 `gap_fit` 輸出到另一個資料夾，**不可覆蓋歷史模型**。
2. 使用 `at_file=data/csc_data_74.xyz` 與 `energy_parameter_name=energy`。
3. 選擇已核對的原始 2-body 與 3-body 設定，確認 3.5 Å cutoff、`n_sparse`（2-body 50、3-body 200）及 `e0_method=average`。
4. 使用原始 energy-only 的 `default_sigma={0.002 0.0 0.0 0.0}`，但完整命令仍需以模型內嵌訓練參數為準。
5. 確認新 XML／SparseX 能被 `quippy` 讀取，再用**相同起始結構、超胞與 Phonopy 設定**計算聲子。
6. 對照既有模型／圖形。若不同，先查訓練參數、QUIP 版本、亂數與結構設定，勿直接宣稱重現失敗或訓練成功。

| 設定 | 用途 |
| --- | --- |
| `at_file` | 輸入資料集 |
| `energy_parameter_name` | 從 XYZ 的哪個欄位讀取總能量 |
| `default_sigma` | 能量、力、virial、Hessian 等標記的噪聲設定；本例只監督能量 |
| `distance_2b` | 二體局域環境描述 |
| `angle_3b` | 三體角度環境描述 |
| `cutoff` | 描述符考慮的鄰域半徑 |
| `n_sparse` | 稀疏環境數；**不是訓練構型數** |
| `gp_file` | 模型輸出 XML 路徑 |

## 第 3 關｜自己產生 DFT 能量訓練集（進階）

在你理解上述流程後，再使用 [ASE 結構生成工具](../../ASE/) 建立 strain、shear、rattle、phonon displacement 構型：

1. 確認參考晶胞、元素排列、超胞與位移尺度。
2. 使用 ASE 產生結構（**rattle 每筆需不同 seed／rng，避免重複**）。
3. 在符合授權與計算資源規定的環境執行 VASP／DFT+gRISB。
4. 檢查真正的計算收斂與能量定義，再將結構＋能量合併成 extended XYZ。
5. 排除錯誤與重複紀錄，留出獨立測試結構；訓練 GAP 後再次跑 Phonopy。

**初學者不需要先完成第 3 關，才能掌握 GAP 與 Phonopy。** 原始 VASP `POTCAR` 等受授權限制檔案不納入本 repo。

## 如何判斷物理結果「合理」？

- 聲子色散：能辨識聲學／光學分支，與相同晶胞、q-path、頻率單位的 DFT 參考比較；不同方法要核對結構與力常數條件。
- 聲子 DOS：應與聲子頻率範圍和模態數一致；若有虛頻須調查結構穩定性及數值設定。
- 熱容：在穩定的三維諧振系統的高溫極限，定容熱容趨近 **3\(k_B\)/atom**（或每莫耳原子 3\(R\)）。
- 熵與 Helmholtz 振動自由能：注意 Phonopy 的單位、正規化與溫度範圍。

**「曲線看起來合理」可以作為流程驗證，但不能替代獨立測試集、力與聲子頻率的定量比較。** 這份教學的第一目標是跑通工作流程，不主張已嚴格驗證新位能的精度。

## 歷史範例的已知限制（簡要但不能省略）

- 原始資料是 **74 筆紀錄／59 個不同幾何**；16 個 rattle frame 重複，是歷史 ASE 腳本在固定 seed 下重新從同一結構位移造成。原始資料與模型將保持不變；新版結構生成器會另行修正。
- 部分歷史 XYZ 的能量與現存 log 的早期 `iter_grisb` 區塊數值相同，但計算曾在 DICOS 執行、原始 log 不完整，無法完全追溯。**不等於現存 `write_xyz.py` 只取第一筆**；該函式實際讀取整份 log 的最後一筆 total energy。
- 此處是 **U=J=0** 的流程測試，不能當成 FeSe 有限 U/J 強關聯效應的驗證。
- 原始 74 筆資料與模型應原樣保存；若日後修正資料並重新訓練，請建立獨立版本與結果。

## 自我檢查題

1. 為什麼只用 `energy` 訓練，也能用 Phonopy 求聲子？
2. `n_sparse=200` 是否代表訓練了 200 個構型？
3. `440 × 128` 的 XYZ 可以直接取代這次 `74 × 32` 的資料嗎？
4. 如果聲子曲線與 DFT 趨勢一致，你能宣稱模型在未見過的構型上已經足夠準確嗎？
5. 哪些步驟不用 VASP 就可以操作？哪些需要重新做參考能量計算？

延伸解釋與常見錯誤請看 [基礎觀念與 FAQ](docs/concepts_and_faq.md)。
