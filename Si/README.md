# Si｜GAP 分子動力學、模型比較與 MACE 訓練

這個資料夾收錄矽（Si）的三個入門範例，另提供 `train_smart.xyz` 與 `test_smart.xyz` 作為 MACE 訓練與驗證資料。請先區分 **QUIP／GAP** 和 **MACE**：它們都是機器學習原子間位能框架，但模型格式、訓練方式與 ASE calculator 不相同。以下程式目前屬於可參考的研究腳本，**尚未像 FeSe U0J0 那樣提供完整模型與端到端重現驗證**。

## 檔案導覽

| 檔案 | 用途 | 使用的模型 |
| --- | --- | --- |
| [MD.py](MD.py) | 從 Si 晶體執行 Langevin NVT 分子動力學 | GAP／QUIP |
| [RMSE.py](RMSE.py) | 比較參考資料與 GAP 的能量、原子力及應力，繪製 parity plots | GAP／QUIP |
| [MACE/](MACE/README.md) | 示範使用 MACE foundation model 微調 energy-only 模型 | MACE |

## Si XYZ 資料與資料集劃分

| 檔案 | 角色 | 用途 |
| --- | --- | --- |
| [train_smart.xyz](train_smart.xyz) | 訓練集 | MACE 的 `--train_file` |
| [test_smart.xyz](test_smart.xyz) | **驗證集**（檔名雖為 test） | 目前 MACE 指令的 `--valid_file` |

兩份都是 extended XYZ。已檢查到 `test_smart.xyz` 的資料欄位包含晶格、座標、`energy`、`forces` 和 `stress`；訓練集也應在執行前用 ASE 檢查標記與單位是否一致。MACE 範例將 forces／virials 的 loss 權重設為 0，因此訓練主要使用能量標記，**不代表檔案必須移除 forces／stress**。

`test_smart.xyz` 目前被訓練指令用來監控驗證誤差及可能的模型選擇，**不能再把同一份資料稱為完全獨立的最終測試集**。若需要宣稱對未知 Si 結構的泛化能力，請另準備未參與訓練、early stopping 和調參的 holdout 資料。

可以從 repository 根目錄執行下列唯讀檢查（需要 ASE、NumPy）：

```bash
python Si/check_datasets.py
```

這個腳本檢查 XYZ 是否可讀、能量是否有限，以及訓練／驗證集是否存在**相同原子順序的重複幾何**；它不是對旋轉、平移、原子排列或晶體對稱性都不變的完整去重工具。正式報告請記錄資料來源、DFT 設定、能量／力／應力單位與資料切分方法。

## 1. GAP 分子動力學：MD.py

**目的：** 學習以 ASE 建立晶體、用 GAP 計算原子力，並透過 Langevin thermostat 模擬有限溫度下的原子運動。

目前腳本的設定：

| 參數 | 設定 |
| --- | --- |
| 初始晶體 | Diamond Si，conventional lattice constant = 5.5063 Å |
| 超胞 | 3×3×3 conventional cells（216 atoms） |
| 溫度／系綜 | 300 K，Langevin NVT |
| 時間步長 | 1 fs |
| 步數 | 20,000（20 ps） |
| 軌跡輸出 | `si_md_NVT.traj`，每 20 步儲存一次 |

**需要自行準備：** 能由 `quippy.potential.Potential` 載入的 `GAP_Si_Final.xml`，以及該 XML 引用的全部 SparseX（若有）。此模型**目前沒有隨 repository 一起提供**。

在安裝好 ASE、NumPy 和 QUIP／quippy，並將模型放在執行目錄後，可從 `Si/` 執行：

```bash
python MD.py
```

程式會在目前工作目錄產生 `si_md_NVT.traj`，終端機列印每一步的位能、動能及瞬時溫度。首次使用時，可先在自己的副本減少 `N_STEPS`，確認模型、環境與輸出正常後再跑完整 20,000 步。

**注意：** 這份腳本會直接執行較長的 MD 計算，並指定執行緒環境變數；請先核對共享伺服器的 CPU 規範。Langevin 的 `friction=0.02` 是 ASE 所採用的時間倒數單位設定，不能直接把程式內的註解「0.002 ps⁻¹」當成正確單位換算；正式研究前應再檢查其物理時間尺度。

## 2. GAP 預測比較：RMSE.py

**目的：** 將 GAP 對同一批 Si 結構預測的能量、力與應力，和參考資料相比，計算 RMSE 並畫出 parity plot。

需要自行準備：

- `GAP_Si_Final.xml`（及其需要的 SparseX）。
- `si_training_easy.xyz`，需包含原子結構及參考能量；若希望比較力或應力，還必須具備對應的參考 labels。
- 可匯入的 ASE、NumPy、Matplotlib、quippy。

從 `Si/` 執行：

```bash
python RMSE.py
```

原始腳本會輸出 `validation_plots_v3_high_res.png`，並顯示能量、力與應力的 RMSE。能量使用 **meV/atom**，力使用 **eV/Å**。

**使用前請確認：**

- 現有腳本假設可取得 *force labels*；**若 XYZ 僅有 energy labels，不能直接用它宣稱 force RMSE，程式也可能因找不到 forces 而停止。**
- `virial` 與 `stress` 並非相同物理量；若來源只有 virial，需要核對正負號與體積換算，再與 GAP stress 比較，不能把原始 virial 直接當作 eV/Å³ 的應力。
- 如果 `si_training_easy.xyz` 就是模型的訓練集，圖中 RMSE 為 **in-sample training error**，不是對未知構型的泛化精度。應另外使用未參與訓練的資料進行真正驗證。

這份程式是**分析範例，尚未提供完整資料與實際執行的驗證結果**。如要改用 energy-only 資料，建議先只比較 energy，再視參考標記的可用性增加力／應力欄位。

## 3. MACE-MP-0 energy-only 微調（已有驗證結果）

[MACE 教學及原始 parity plots](MACE/README.md) 收錄已跑完的訓練／驗證分析、checkpoint SHA-256，以及 [重新評估程式](MACE/evaluate_parity.py)。

| 評估集 | 結構數 | Energy RMSE (meV/atom) | Force RMSE (meV/Å) | Stress RMSE (eV/Å³) |
| --- | ---: | ---: | ---: | ---: |
| Training：train_smart.xyz | 190 | 2.07 | 153.90 | 0.0025 |
| Validation：test_smart.xyz | 22 | 3.10 | 162.28 | 0.0022 |

結果使用 float64、r_max=5 Å 的 MACE-MP-0 energy-only 微調 Stage Two（SWA）模型。Force／Stress 的損失權重為 0，但 foundation model 已經過預訓練；不能把 force 預測完全歸功於本次 Si 能量微調。RMSE 分別取每筆能量/原子、所有力笛卡兒分量、ASE stress 六個 Voigt 分量計算。

目前的 test_smart.xyz 被指定為訓練過程的 validation file，**不是獨立的 holdout test**；建議再核對資料來源與幾何重複情況。

MP0指令 使用 MACE-MP-0 float64；沒有MP0 檔名具有誤導性，它仍載入 float32 的預訓練 foundation model，並非從零訓練。兩個範例都不適用於直接載入 QUIP／GAP XML。
## 下一步

Si 的 QUIP／GAP 已有 MD.py 與 RMSE.py 範例，暫時**不需要再複製一整套 QUIP 版本**。若要做真正的 GAP vs MACE 比較，應先補上可合法分享的 GAP_Si_Final.xml（與必要 SparseX）、si_training_easy.xyz 的來源及兩模型一致的評估集。未知構型的能力仍需獨立 holdout 驗證。

如果想從完整資料與指令一步步操作，建議先學習已驗證的 [FeSe GAP → Phonopy 教學](../FeSe/VASP/QUIP/U0J0_pretest/README.md)。
