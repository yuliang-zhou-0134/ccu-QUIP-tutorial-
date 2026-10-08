# ASE｜FeSe 結構生成與能量擷取

本目錄提供 FeSe energy-only 訓練資料準備工具，產生的 POSCAR 通常仍需送交 VASP（或 VASP+gRISB）計算能量。

| 程式 | 用途 |
| --- | --- |
| `strain.py` | 從設定的 POSCAR 產生等比例與 c 軸應變構型，並可複製本地存在的 VASP 輸入檔 |
| `rattle.py` | 建立 `2×2×2` 超胞、產生隨機原子位移並建立 SCF/CSC 任務資料夾 |
| `shear.py` | 在 `2×2×2` 超胞中平移上層原子，產生剪切位移 |
| `phonopy_disp.py` | 以 Phonopy 有限位移生成 `2×2×2` 超胞與 SCF/CSC 計算目錄 |
| `create_xyz.py` | 由已完成的 SCF/CSC 計算擷取 POSCAR 與能量，分別輸出 extended XYZ |

## 建議準備順序

1. 以適當的 FeSe 結構產生 strain/rattle/shear/phonon displacement 構型。
2. 在一致的計算設定下取得各構型的參考能量，先確認計算收斂與構型對應。
3. 整理為 extended XYZ，檢查元素順序、晶格、單位與每一筆 energy。
4. 再交由 QUIP/GAP 訓練及後續 Phonopy 分析。

## 輸出 XYZ 範例

從儲存庫根目錄：

```bash
python FeSe/VASP/ASE/create_xyz.py /path/to/calculation_root \
    --csc-out csc_data.xyz --scf-out scf_data.xyz
```

此程式預期計算目錄存在 `scf/`、`csc/`，SCF 從 `OUTCAR` 抓取 free energy，CSC 從 `nohup.out` 抓取 total energy 並以尾端特定字串判斷收斂。若實際 log 格式不同，請先調整擷取邏輯，並**不要直接混用兩套能量定義**。

> **執行前注意：** 上述結構生成腳本仍具有硬編碼輸入檔名及相對路徑；有些 VASP/gRISB 執行腳本和 POTCAR 因授權或環境差異並未隨 repo 提供。應先檢查每個工具的預期工作目錄、POSCAR 與超胞尺寸。
