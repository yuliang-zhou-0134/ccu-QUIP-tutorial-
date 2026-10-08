# QUIP／GAP｜FeSe energy-only 訓練

本目錄包含 GAP 訓練指令範例、FeSe extended XYZ 資料集及模型弛豫程式。

| 檔案 | 用途 |
| --- | --- |
| `QUIP指令` | 終端機中使用 MPI 執行 `gap_fit` 的範例 |
| `energy_only_dataset.xyz` | FeSe energy-only extended XYZ：**440 筆構型、每筆 128 顆原子**（`4×4×2` 超胞） |
| `relax.py` | 以 `quippy.potential.Potential` 與 ASE `BFGS` 執行結構／晶胞弛豫 |

## 訓練設定摘要

`QUIP指令` 的 GAP 模型組合了：
- **distance_2b**（cutoff 5.0 Å；`n_sparse=70`）
- **SOAP**（cutoff 3.5 Å；`n_sparse=700`）
- **angle_3b**（cutoff 3.5 Å；`n_sparse=200`）

指令也指定 `energy_parameter_name=energy`、`default_sigma={0.0005 0.0 0.0 0.0}` 及兩個元素的 `e0`。它們只是**現有範例的設定值**，不應解讀成對不同資料量、晶胞或參考電子結構方法都最佳。尤其 `e0` 是與能量定義相關的參考量，必須配合新的資料確認。

指令檔使用 `gap_fit`、`mpirun`、QUIP／MPI 環境；請先確認本地的執行路徑和輸出模型檔名。

**資料版本提醒：** 現有 `QUIP指令` 直接以 `at_file=energy_only_dataset.xyz` 讀取 440 筆構型，沒有指定 74 筆篩選。研究者已確認兩張結果圖使用 **74 筆 CSC（charge-self-consistent）總能量訓練構型**，經 GAP energy-only 訓練與 Phonopy 計算，屬 **U=J=0 的 pre-test**。兩者不可當成相同資料集；`n_sparse` 是稀疏環境數，並非訓練構型筆數。

## 弛豫

`relax.py` 預設讀取工作目錄中的 `POSCAR`，且 `GAP_XML` 目前設為特定實驗用模型路徑。執行前必須修改指向實際存在的模型 XML，並核對輸入結構是否與程式中晶胞尺寸假設相符。

## 模型評估

目前此目錄沒有完整的獨立驗證資料分割與 RMSE 表格；需先決定 train/validation 的構型切分，避免以訓練資料本身當作泛化性能證明。聲子工作流程另請參閱 [../phonopy/](../phonopy/)。
