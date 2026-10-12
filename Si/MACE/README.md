# MACE｜Si energy-only 訓練指令範例

本資料夾提供在 Google Colab／GPU 環境中嘗試過的訓練指令。若於一般終端機執行，需移除 Colab 的 `!` 前綴，並備妥環境及資料檔。

## 現有指令

- `MP0指令`：`--foundation_model="mace_mp.model"`，使用預訓練模型進行微調。現有設定採 `r_max=5.0`、`float64`、200 epochs。
- `沒有MP0`：**檔名具有誤導性。** 目前內容仍設定 `--foundation_model="mace_mp_f32.model"`，因此也是**使用預訓練權重的微調示例**，並非真正的從零訓練。現有設定為 `float32`、100 epochs。

兩份指令都將 `forces_weight`、`virials_weight` 及對應 SWA 權重設為零，以總能量作為主要訓練標記；`energy_weight` 等權重需配合資料及 MACE 版本檢查。

## 需要自行準備

- 相容版本的 MACE、PyTorch 和 GPU/CPU 環境。
- [../train_smart.xyz](../train_smart.xyz) 和 [../test_smart.xyz](../test_smart.xyz) 已收錄，分別對應 `--train_file` 和 `--valid_file`。`test_smart.xyz` 在目前指令中是驗證集，而非與模型選擇無關的最終測試集。
- 指令指定的 foundation model 檔，例如 `mace_mp.model` 或 `mace_mp_f32.model`。

兩份指令預設從執行目錄讀取 XYZ；若在 `Si/MACE/` 內執行，需將檔案參數改為 `../train_smart.xyz`、`../test_smart.xyz`，或在 `Si/` 執行並將指令與模型路徑設定正確。真正的未知結構評估仍需要額外的獨立 holdout 資料。

下載與安裝請參閱 [MACE 官方專案](https://github.com/ACEsuit/mace)，並核對 foundation model 的授權、模型版本及能量參考定義。

> 如果真正要做**不使用 MP0、從頭訓練**的 MACE recipe，應另建立不含 `--foundation_model` 的版本，不要直接把目前 `沒有MP0` 當作從零訓練。
