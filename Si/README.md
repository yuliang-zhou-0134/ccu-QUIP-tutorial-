# Si｜GAP、MACE、ASE 與 Phono3py 教學

這個目錄使用同一組 Si extended-XYZ 資料，示範兩條不同的 MLIP 路線：從頭訓練的 **QUIP/GAP Energy-only**，以及以 foundation model 起步的 **MACE-MP Energy-only fine-tuning**。兩者的模型格式、calculator 與訓練背景不同，請勿交叉載入。

## 建議學習順序

1. 先用 ASE 讀取 `train_smart.xyz` 與 `test_smart.xyz`，理解結構、total energy、forces、stress labels。
2. 依 [`GAP/README.md`](GAP/README.md) 產生只含 energy label 的 XYZ，閱讀 `gap_fit` 參數，載入已完成模型並重算 RMSE。
3. 再閱讀 [`MACE/README.md`](MACE/README.md)，比較 foundation-model fine-tuning 與從頭訓練的差異。
4. 用 [`check_datasets.py`](check_datasets.py) 檢查筆數、有限值與完全相同原子順序的重複幾何。

## 資料與目錄

| 路徑 | 內容 |
| --- | --- |
| `train_smart.xyz` | Training，190 個結構；含 energy、forces、stress |
| `test_smart.xyz` | Validation，22 個結構；含 energy、forces、stress |
| [`GAP/`](GAP/README.md) | Si GAP Energy-only 資料準備、訓練、模型與實算結果 |
| [`MACE/`](MACE/README.md) | MACE-MP Energy-only fine-tuning、parity plots 與 Phono3py |
| [`MD.py`](MD.py)、[`RMSE.py`](RMSE.py) | 舊 `GAP_Si_Final.xml` 範例，保留但不屬於新 Energy-only 模型 |

`test_smart.xyz` 在兩條流程中都是 validation set，不是完全獨立的 holdout test。要研究未知構型的泛化能力，仍應另準備未參與訓練、選模與調參的 test set。

目前的有序幾何檢查沒有發現 Training–Validation 交集，但 Training 第 21 與 35 號 frame（從 0 起算）完全相同，所以 190 筆中只有 189 個不同的有序幾何。現有模型確實以 190 筆訓練；重新設計資料集時應先處理這個重複構型。

## 已完成的 Validation 結果

| 模型 | 訓練背景 | Energy RMSE | Force RMSE | Stress RMSE |
| --- | --- | ---: | ---: | ---: |
| Si GAP Energy-only | 從頭訓練，只用本資料 energy | 6.98423 meV/atom | 0.197241 eV/Å | 0.006971 eV/Å³ |
| MACE-MP Energy-only | foundation model fine-tuning | 3.10 meV/atom | 0.16228 eV/Å | 0.0022 eV/Å³ |

這張表不是純架構的公平競賽。GAP 從零開始；MACE-MP 已具有大型預訓練資料帶來的先驗知識，即使本次 fine-tuning 把 force／virial loss weight 設為 0，其 force／stress 預測仍可能受預訓練影響。兩者都以每結構 energy/atom、所有 force 笛卡兒分量、ASE stress 六個 Voigt 分量計算 RMSE。

## 新舊 GAP 的界線

新模型固定命名為 `GAP_Si_EnergyOnly.xml`，只收在 `Si/GAP/model/`；其 Training／Validation 結果只收在 `Si/GAP/results/`。舊 `GAP_Si_Final.xml` 流程使用 energy 加上 force／virial-stress 相關監督，不得稱為 Energy-only。本次保留既有 `MD.py`、舊 `RMSE.py`、MACE 與 FeSe 教材，不以新模型覆寫。

若想先看另一個完整 GAP → Phonopy 範例，可閱讀 [FeSe U0J0 教學](../FeSe/VASP/QUIP/U0J0_pretest/README.md)。
