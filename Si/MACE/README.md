# Si｜MACE-MP-0 energy-only 微調與評估

本範例使用預訓練 **MACE-MP-0（Medium）**，以 Si DFT 能量進行 **energy-only fine-tuning**。微調的 force／virial 損失權重設為零，但保留 DFT energy、forces、stress labels 供模型評估。請勿將 MACE checkpoint 用在 GAP／QUIP calculator。

## 已驗證的結果

| 項目 | 設定 |
| --- | --- |
| Foundation | mace_mp.model（MACE-MP-0） |
| 訓練完成 checkpoint | Si_MACE_only_energy_r_max5_TRUE_BLIND_run-123_stagetwo.model |
| SHA-256 | 929b2f5bf41f32f2eea1d0346e78a5c4f6d1d781d8167fa356b7ff87251ac549 |
| 環境／精度 | MACE 0.3.14、float64 |
| r_max | 5.0 Å |
| 微調 | 200 epochs；SWA 從 epoch 150 開始；seed 123 |
| Loss | Energy weight 10；force/virial（含 SWA）weight 0 |
| Training | [train_smart.xyz](../train_smart.xyz)，190 個結構 |
| Validation | [test_smart.xyz](../test_smart.xyz)，22 個結構 |

Checkpoint 權重**未收錄於 repository**，但其名稱和 SHA-256 已記錄。另一份檔名沒有 run-123 的模型雖然檔案 SHA 不同，在 22 筆 validation 結構上的 energy／force 預測與 checkpoint 幾乎完全一致；本頁圖片改以訓練紀錄明確指定的 run-123 checkpoint 重新評估。

| 評估集 | Energy RMSE | Force RMSE | Stress RMSE |
| --- | ---: | ---: | ---: |
| Training (190) | 2.07 meV/atom | 153.90 meV/Å | 0.0025 eV/Å³ |
| Validation (22) | 3.10 meV/atom | 162.28 meV/Å | 0.0022 eV/Å³ |

### Validation：DFT vs MACE

![Si MACE validation energy, force and stress parity](results/validation_parity.png)

### Training：DFT vs MACE

![Si MACE training energy, force and stress parity](results/training_parity.png)

圖片來自已完成的 Colab Notebook「MACE_for_Silicon_only_energy_r_max5 (3).ipynb」的兩個評估 cell；**不是示意圖**。Force 散點為最多 1000 個分量的繪圖抽樣，但圖上 RMSE 使用全部原子力分量。Stress 為 ASE get_stress() 的六維 Voigt 應力（eV/Å³），不是直接拿 virial 當 stress。

**如何解讀：** 這不是「從零開始只用 Si energy 訓練」的模型，而是已有預訓練知識的 MACE-MP。test_smart.xyz 在訓練指令內是 validation file，**不是最終獨立 holdout**。train／validation 的完整資料來源與對稱等價去重尚未完成，因此不宜宣稱已證明未知結構的泛化能力。可先執行 repository 內的 python Si/check_datasets.py，檢查有序幾何是否重複；它不包含晶體對稱判別。

可機讀的來源與數字見 [results/metrics.json](results/metrics.json)。

## 重現 parity plots（無須再訓練）

需要 ASE、NumPy、Matplotlib、PyTorch、MACE。模型請使用你自己訓練或可信來源的完整 checkpoint。從 repository 根目錄執行：

~~~bash
python Si/MACE/evaluate_parity.py \
  --model /path/to/Si_MACE_only_energy_r_max5_TRUE_BLIND_run-123_stagetwo.model
~~~

程式會自動使用 CUDA 或 CPU；可用 --device cuda 或 --device cpu 指定。只需 validation 圖可加 --split validation。它先讀 DFT 參考值再安裝 MACECalculator，並固定 force 繪圖抽樣種子；新的 PNG 與 metrics.json 輸出於 Si/MACE/results/recomputed/，**不會覆寫此頁歷史圖**。

## 兩份原始訓練指令

- [MP0指令](MP0指令)：載入 mace_mp.model，float64、200 epochs、SWA 150；本頁主要實驗。
- [沒有MP0](沒有MP0)：名稱具有誤導性；仍指定 mace_mp_f32.model，因此也是 foundation-model fine-tuning，而非從頭訓練（float32、100 epochs）。

這兩份是 Colab 指令，以 !python3 開頭；若在一般終端機執行請移除 !。模型與 XYZ 路徑是相對於執行目錄；原始資料在上一層 Si/，建議在 Si/ 執行或調整 --train_file 與 --valid_file。foundation model 的授權、版本及詳細安裝資訊見 [MACE 官方專案](https://github.com/ACEsuit/mace)。

## 聲子與熱導率：仍在整理

同一個 Stage Two checkpoint 已用於 Phonopy／Phono3py 的 Si 計算。不過新版熱導率 q-mesh／溫度掃描**還在進行**；目前不將舊版單一熱導率值視為收斂結果，也不混用不同晶格設定、模型或超胞。等到 Colab 完成掃描並確認輸出檔後，再收錄帶有模型 SHA、晶格、超胞、位移、q-mesh 與近似方法（RTA 等）的正式圖片。
