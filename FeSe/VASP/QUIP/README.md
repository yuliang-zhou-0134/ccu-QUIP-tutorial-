# QUIP／GAP｜FeSe energy-only 訓練

本目錄包含 GAP 訓練指令範例、FeSe extended XYZ 資料集、模型弛豫程式，以及已驗證的 [U=J=0 教材](U0J0_pretest/)。

| 檔案 | 用途 |
| --- | --- |
| `QUIP指令` | 終端機中使用 MPI 執行 `gap_fit` 的範例 |
| `energy_only_dataset.xyz` | FeSe energy-only extended XYZ：**440 筆構型、每筆 128 顆原子**（`4×4×2` 超胞） |
| `relax.py` | 以 `quippy.potential.Potential` 與 ASE `BFGS` 執行結構／晶胞弛豫 |
| `U0J0_pretest/` | 74 筆紀錄（59 個不同幾何）的完整入門教材；含歷史 GAP、Phonopy／DFT 輸入與重訓腳本 |

## 訓練設定摘要

`QUIP指令` 的 GAP 模型組合了：
- **distance_2b**（cutoff 5.0 Å；`n_sparse=70`）
- **SOAP**（cutoff 3.5 Å；`n_sparse=700`）
- **angle_3b**（cutoff 3.5 Å；`n_sparse=200`）

指令也指定 `energy_parameter_name=energy`、`default_sigma={0.0005 0.0 0.0 0.0}` 及兩個元素的 `e0`。它們只是**現有範例的設定值**，不應解讀成對不同資料量、晶胞或參考電子結構方法都最佳。尤其 `e0` 是與能量定義相關的參考量，必須配合新的資料確認。

這份 440-frame 指令檔使用 `gap_fit`、`mpirun`、QUIP／MPI 環境；請先確認本地的執行路徑和輸出模型檔名。U0J0 教材則因本機 `gap_fit` 與 PATH 上 `mpirun` 的 Open MPI 版本不同，已驗證採單一直接 `gap_fit` process，不可照抄此處的 MPI 啟動方式。

**資料版本提醒：** 現有 `QUIP指令` 直接以 `at_file=energy_only_dataset.xyz` 讀取 440 筆構型。U0J0 教材另存當次 **74 筆 CSC 總能量紀錄**於 `U0J0_pretest/data/csc_data_74.xyz`，並以 SHA-256 鎖定；它不是 440 筆資料的篩選子集。兩者不可混用；`n_sparse` 是稀疏環境數，並非訓練構型筆數。

U0J0 的 `training/train_gap.sh` 已逐項還原歷史 XML command line，實測可於 1 CPU 完成重訓。新的 XML/SparseX 不必逐 byte 等於歷史模型；應比較相同結構上的 energy、forces 與 4×4×4 Phonopy。74-frame energy MAE/RMSE 是 training-set residual，不是獨立驗證精度。

## 弛豫

`relax.py` 預設讀取工作目錄中的 `POSCAR`，且 `GAP_XML` 目前設為特定實驗用模型路徑。執行前必須修改指向實際存在的模型 XML，並核對輸入結構是否與程式中晶胞尺寸假設相符。

## 未來工作：未知結構的能量預測

就本目錄的 **440-frame FeSe 資料範例**而言，目前尚未針對**未納入訓練資料的 FeSe 結構**進行獨立的能量預測驗證，相關計算有待補足。未來可使用修正後的 [ASE/rattle.py](../ASE/rattle.py) 產生與訓練資料不重複的隨機位移構型，再利用 GAP 預測其總能量。

若要進一步評估模型對未知結構的準確度，仍需對**相同的新構型**計算 DFT 參考能量，與 GAP 預測值比較；僅取得 GAP 的預測能量，無法判斷誤差大小。產生測試資料時，也應避免與訓練集出現重複幾何。一般聲子腳本請參閱 [../phonopy/](../phonopy/)，完整的 GAP → Phonopy 入門流程請參閱 [U0J0_pretest/README.md](U0J0_pretest/README.md)。
