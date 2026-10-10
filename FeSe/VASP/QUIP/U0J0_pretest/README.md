# FeSe U=J=0｜DFT energy → extended XYZ → GAP → Phonopy

這是一份給新進學生操作的完整範例。它保存歷史的 74 筆 CSC energy-only 資料與既有 GAP，不重新執行 VASP 或 DFT+gRISB，也不更動歷史模型；新訓練與新 Phonopy 結果一律寫到新的 output 路徑。

> 這是 U=J=0 的流程教學，不是 FeSe 強關聯物理的定量驗證。歷史資料有 74 筆紀錄，但只有 **59 個不同幾何構型**；frames 33–48 是同一幾何的 16 次重複紀錄。為保留可追溯性，XYZ 與原始模型均原樣保留。

## 流程一覽

```text
DFT/CSC total energy
        ↓
extended XYZ（結構、晶格、energy）
        ↓
QUIP gap_fit（2-body + 3-body，energy-only）
        ↓
GAP E(R) 與 F=-∂E/∂R
        ↓
Phonopy finite displacement
        ↓
聲子色散、DOS、Cv、S、振動 Helmholtz free energy
```

Energy-only 是指訓練標記只有總能量；Phonopy 仍使用 GAP 對能量微分得到的預測力。詳細觀念見 [docs/concepts_and_faq.md](docs/concepts_and_faq.md)。

## 檔案與來源

```text
U0J0_pretest/
├── data/csc_data_74.xyz
├── model/
│   ├── csc_ver.xml
│   └── csc_ver.xml.sparseX.GAP_..._6711～6719
├── training/
│   ├── train_gap.sh
│   └── validate_retrained_model.py
├── scripts/
│   ├── check_assets.py
│   └── model_smoke_test.py
├── phonon/
│   ├── POSCAR
│   ├── CONTCAR
│   ├── csc_ver.yaml
│   ├── ground_truth.yaml
│   ├── reference_dft/FORCE_CONSTANTS
│   ├── run_gap_phonopy.py
│   ├── thermal.py
│   └── compare_phonons.py
├── results/
│   ├── phonon_comparison_historical.png
│   └── thermal_properties_historical.png
└── checksums.sha256
```

- `data/csc_data_74.xyz`：原始 74-frame extended XYZ，32 atoms/frame，energy 單位為整個構型的 eV。
- `model/csc_ver.xml`：歷史 GAP。XML 真正引用的是 `6711`–`6719` 共 9 個 SparseX；來源目錄中的 `6601`–`6609` 是內容相同但未被此 XML 引用的副本，故未納入。
- `phonon/POSCAR`、`CONTCAR`：原始來源目錄中的起始與歷史弛豫結構。歷史 `plot_phonon.py` 是從 POSCAR 做 hydrostatic cell relaxation；新的 `run_gap_phonopy.py` 保留這個選擇。
- `phonon/csc_ver.yaml`：歷史 GAP finite-displacement 資料，4×4×4 supercell。
- `phonon/ground_truth.yaml` 加 `reference_dft/FORCE_CONSTANTS`：DFT 比較所需資料。只提供 YAML 不足以重建此 DFT 曲線，因此一併保存 FORCE_CONSTANTS。
- `results/*_historical.png`：從研究資料夾原樣複製的歷史圖，不是本次重新計算的結果。
- `checksums.sha256`：上述歷史輸入與輸出的 SHA-256，可用來確認沒有改動。

不要混用上一層的 `energy_only_dataset.xyz`；它是另一組 440×128 資料，訓練設定也不同。

## 測試狀態（2026-10-10）

| 狀態 | 項目 | 結果 |
| --- | --- | --- |
| ✅ 已通過 | XYZ 結構檢查 | 74 frames、每筆 Fe16Se16／32 atoms、74 筆皆有 energy |
| ✅ 已通過 | 重複幾何檢查 | 59 個不同幾何；frames 33–48 為同一幾何 |
| ✅ 已通過 | GAP 檔案完整性 | XML 可解析；9 個 SparseX 都存在且 MD5 與 XML 一致 |
| ✅ 已通過 | 既有模型單點 smoke test | frame 0 可算有限 energy 與 32×3 forces |
| ✅ 已通過 | Python／shell 靜態檢查 | 教學腳本無 repository 外硬編碼路徑 |
| ✅ 已通過 | 2×2×2、skip-relax GAP → Phonopy smoke test | 4 個位移構型；forces／force constants 皆有限；YAML 可重新載入 |
| ✅ 已通過 | 歷史 `csc_ver.yaml` 直接重畫 | 700×12 頻率陣列；最低頻率為數值零；圖形正常 |
| ✅ 已通過 | 歷史 relaxed cell 的 4×4×4 GAP → Phonopy | 新舊頻率最大差 2.69×10⁻⁶ meV、RMS 5.25×10⁻⁸ meV |
| ✅ 已通過 | 4×4×4 YAML 振動熱力學 | 30³ mesh；1000 K 的 Cv 為 2.96790 kB/atom；CSV、圖與 JSON 均已輸出 |
| ✅ 已通過 | DFT／重現 GAP 聲子比較 | 相同 700 q-points、12 branches、meV；MAE 1.62477 meV、RMSE 2.11048 meV |
| ✅ 已通過 | GAP retraining preflight | XML 參數逐字一致；74-frame SHA-256 鎖定；gap_fit／函式庫可載入；未啟動訓練 |
| ✅ 已通過 | 74-frame `gap_fit` 重新訓練 | 1 process、7.16 秒、63,024 KiB；新 XML＋9 SparseX 可完整載入 |
| ✅ 已通過 | 重訓模型行為驗證 | 74 筆 energy／forces 全部 finite；新舊 energy MAE 2.60×10⁻⁷ eV/config |
| ✅ 已通過 | 重訓模型 4×4×4 GAP → Phonopy | 聲子 MAE 0.00387 meV、RMSE 0.00471 meV；無實質虛頻 |
| 🚫 不在範圍 | VASP／DFT+gRISB 重跑 | 本教學不執行 |

本機單點 smoke test 的實際結果：

```text
reference energy:      -225.7860979000 eV
GAP energy:            -225.7860782191 eV
GAP - reference:          0.0000196809 eV
forces shape:                 (32, 3)
max |force|:               0.0784306319 eV/Å
```

這只證明 XML＋SparseX 能被讀取並產生有限值；不能當成獨立測試誤差。

## 實測環境

本次低成本測試記錄：

```text
Python       3.10.19
NumPy        1.26.4
ASE          3.28.0
Phonopy      3.2.1
Matplotlib   3.10.8
PyYAML       5.4.1
QUIP         v0.10.2-dirty, linux_x86_64_gfortran
              compiled 2026-02-23 15:27:34
```

預設 Python 雖有 ASE／Phonopy，卻沒有可直接 import 的 `quippy`。可用的 QUIP Python binding 還需要同環境中的 `f90wrap`；本機是以既有 `atom_sim` conda environment 加 QUIP build 的 `PYTHONPATH` 通過 smoke test。不同機器請安裝相容的 `quippy-ase`，或使用同一 QUIP build 所產生的 Python binding。

最低依賴：

- 資料檢查：Python、NumPy、ASE。
- 模型推論／Phonopy forces：以上加 quippy（須能讀取此 QUIP XML）。
- 重新訓練：QUIP 的 `gap_fit`。
- 聲子與繪圖：Phonopy、Matplotlib；PyYAML 供一般 YAML 工具使用。

## 執行目錄（重要）

**以下所有教學指令都以 `FeSe/VASP/QUIP/U0J0_pretest/` 為目前工作目錄**，包括 `python scripts/...`、`python phonon/...` 和 `bash training/...`；不要直接在 GitHub repository 根目錄執行這些相對路徑指令。

第一次操作時，請先從 repository 根目錄進入教學資料夾：

```bash
cd FeSe/VASP/QUIP/U0J0_pretest
```

之後的各關都沿用此工作目錄。如果重新開啟終端機，請先確認 `pwd`，必要時重新切換到這個教學資料夾。**以下不再重複 `cd`**。

## 第 0 關：低成本完整性檢查

在上述教學資料夾執行：

```bash
sha256sum --check checksums.sha256
python scripts/check_assets.py
python -m py_compile scripts/*.py phonon/*.py
bash -n training/train_gap.sh
```

預期看到 SHA-256 全部 `OK`，以及：

```text
PASS XYZ: 74 records, 32 atoms each, 59 unique geometries
PASS model: XML parses and all 9 referenced SparseX MD5 values match
```

## 第 1 關：使用現成 GAP 模型計算聲子

必要輸入是 `model/csc_ver.xml`、XML 引用的 9 個同目錄 SparseX，以及歷史 relaxed cell 所在的 `phonon/csc_ver.yaml`。先以 32-atom frame 做最低成本的模型讀取測試：

若 `quippy` 已安裝：

```bash
python scripts/model_smoke_test.py
```

如果 QUIP binding 位於自建目錄，可將路徑由環境指定，不要寫死進腳本：

```bash
export QUIP_PYTHON_BUILD=/path/to/QUIP/build/<QUIP_ARCH>
PYTHONPATH="$QUIP_PYTHON_BUILD" python scripts/model_smoke_test.py
```

常見錯誤：

- `No module named quippy`：目前 Python 沒看到 QUIP binding。
- `No module named f90wrap`：binding 已找到，但此 Python 缺少 QUIP 建置時需要的 f90wrap。
- 找不到 SparseX：XML 與 9 個 SparseX 必須留在同一個 `model/`。
- MD5 mismatch：檔案被修改、改錯版本或複製不完整；先比對 `checksums.sha256`。

### 1.2 GAP → Phonopy 流程測試

先做第 1 關，然後才執行：

```bash
python phonon/run_gap_phonopy.py
```

預設會：

1. 讀取 `phonon/POSCAR`。
2. 依歷史腳本做 hydrostatic cell relaxation。
3. 建立 4×4×4（256 atoms）supercell 與 0.01 Å 位移。
4. 用 GAP 算 perfect cell 與 displaced cells 的力，扣除 background force。
5. 將新 YAML、弛豫結構、log、trajectory 與聲子圖寫到 `phonon/output/`。

歷史檔永遠不會被預設輸出覆蓋；若 output 已存在，腳本會停止。快速除錯可先另指定較小測試：

```bash
python phonon/run_gap_phonopy.py \
  --supercell 2 2 2 \
  --skip-relax \
  --output-dir phonon/output_smoke
```

2×2×2 只能測流程，不可拿來宣稱重現歷史 4×4×4 結果。

2026-10-09 的實測使用 1 CPU、1 GiB virtual-memory 上限與 300 秒 timeout，程序在 15.96 秒完成，maximum RSS 為 174,048 KiB（169.97 MiB）。輸出 YAML 可正常重新載入；force array 為 `(4, 32, 3)`，compact force constants 為 `(4, 32, 3, 3)`，全部是有限值。未弛豫 POSCAR 的最大背景力分量為 3.29072996 eV/Å；沿教學 q-path 的最低頻率為 −1.829399 THz（−7.565788 meV），所以這個 smoke test **只驗證流程，不代表穩定聲子結果**。完整 smoke-test output 是可重新產生的工作檔，因此不納入 Git；上列數值已保留於本教材。

預期輸出：

```text
phonon/output/
├── CONTCAR_gap_reproduced
├── relax.log
├── relax.traj
├── csc_ver_reproduced.yaml
└── phonon_gap_reproduced.png
```

### 1.3 已驗證的歷史 4×4×4 重現路徑

正式重現不使用未弛豫 POSCAR，也不使用 fully relaxed CONTCAR；它直接從 `csc_ver.yaml` 讀取當次 hydrostatic-relaxed unit cell。先確認歷史 YAML 可獨立重畫：

```bash
python phonon/redraw_historical.py \
  --output-dir phonon/output_history_redraw
```

再用同一 unit cell、原始 GAP、4×4×4 supercell 與歷史 0.01 Å 位移重算 forces：

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
ulimit -v 2097152
timeout 600s taskset -c 0 \
  python phonon/reproduce_historical_4x4.py \
  --output-dir phonon/output_reproduction_4x4
```

腳本會先核對重新產生的四個位移原子索引與位移向量是否和歷史 YAML 一致，然後才呼叫 GAP。力的處理與原始腳本相同：先計算 perfect supercell 的 background force，位移結構力減去 background，再 `produce_force_constants()` 與 `symmetrize_force_constants()`。

2026-10-09 實測結果：

| 指標 | 結果 |
| --- | ---: |
| Supercell／原子數 | 4×4×4／256 atoms |
| 位移結構 | 4；每個位移 0.01 Å |
| 最大 background force component | 5.573×10⁻⁷ eV/Å |
| 新舊 displaced-force 最大差 | 5.706×10⁻¹³ eV/Å |
| 新舊 displaced-force RMS 差 | 1.636×10⁻¹³ eV/Å |
| 新舊頻率最大絕對差 | 2.690×10⁻⁶ meV |
| 新舊頻率 RMS 差 | 5.252×10⁻⁸ meV |
| 歷史／重現最低頻率 | −1.636×10⁻⁶／−2.309×10⁻⁶ meV（皆為數值零） |
| 歷史／重現 Γ–Z 最大 branch span | 5.705606／5.705606 meV |
| 執行時間／maximum RSS | 25.59 s／717,044 KiB（約 700 MiB） |

結果可判定為成功重現。完整 machine-readable 指標在 `phonon/output_reproduction_4x4/reproduction_metrics.json`；新 YAML、單獨頻譜與新舊疊圖都位於同一 output 目錄，沒有覆寫歷史 YAML。

物理上，finite displacement 是以小位移後的 restoring forces 建立二階力常數；其本徵值給出聲子頻率。常見錯誤包括錯用未弛豫 POSCAR、忘記扣背景力、XML 和 SparseX 分離、THz/meV 混用，以及把 2×2×2 smoke test 誤當正式 4×4×4 結果。

## 第 2 關：計算 Phonon DOS 與振動熱力學

輸入是第 1 關產生且已通過 reload 測試的
`phonon/output_reproduction_4x4/csc_ver_reproduced_4x4.yaml`。它已含力常數；本步不載入 GAP、不產生位移，也不重算 forces。

歷史 `thermal.py` 的設定是 30×30×30 mesh、停用 mesh symmetry、0–1000 K、每 10 K 一點。請在前述 `U0J0_pretest/` 工作目錄執行：

```bash
python phonon/thermal.py \
  --input phonon/output_reproduction_4x4/csc_ver_reproduced_4x4.yaml \
  --historical-yaml phonon/csc_ver.yaml \
  --mesh 30 30 30 \
  --t-min 0 --t-max 1000 --t-step 10 \
  --output-dir phonon/output_thermal_reproduction
```

預期輸出：

```text
phonon/output_thermal_reproduction/
├── thermal_properties_reproduced.png
├── thermal_properties.csv
├── phonon_dos.csv
└── thermal_metrics.json
```

物理意義：DOS 顯示各頻率可用的振動模態密度；`Cv` 是定容振動熱容；entropy 是振動熵；Helmholtz free energy 是諧振近似下的振動自由能。Phonopy 回傳的熱容與熵為每 mole primitive cell 的 J/K/mol，自由能為 kJ/mol primitive cell。本例 primitive cell 有 4 atoms，因此以 `Cv/(4R)` 轉成每原子的 `kB`。

2026-10-10 實測：

| 溫度 | Cv (kB/atom) | Entropy (J/K/mol cell) | Free energy (kJ/mol cell) |
| ---: | ---: | ---: | ---: |
| 0 K | 0 | 0 | 16.44416 |
| 300 K | 2.67444 | 110.88212 | 0.14077 |
| 1000 K | 2.96790 | 225.85146 | −125.00357 |

1000 K 的 `Cv` 已達 `3kB/atom` 的 98.93%，符合 Dulong–Petit 高溫極限。和歷史 YAML 在相同 grid 重算後，Cv、entropy、free energy 的最大差分別為 `1.77×10⁻¹¹ J/K/mol`、`4.12×10⁻¹¹ J/K/mol`、`3.75×10⁻¹¹ kJ/mol`。

新舊圖的 DOS 峰位及三條熱力學曲線形狀一致。歷史圖沒有保存原始數據，而且舊腳本將 THz 頻率軸換成 meV 時沒有把 DOS 高度由 `1/THz` 同步換成 `1/meV`；新 CSV 與新圖使用一致的 meV／`1/meV`，所以 DOS 峰高會與歷史圖相差固定的換算因子，不能做像素高度比較。

常見錯誤：

- `force constants are missing`：輸入 YAML 不是第 2 關的 self-contained YAML，或保存時沒有包含 force constants。
- output 已存在：腳本刻意拒絕覆寫；改用新的 `--output-dir`。
- 記憶體或時間明顯上升：先確認沒有誤把 mesh 寫成 supercell 大小；30³ 是 q-point mesh，不是 30³ 原子超胞。
- NumPy 1.26 沒有 `np.trapezoid`：教學腳本已使用相容的 `np.trapz`。

## 第 3 關：與 DFT 參考聲子比較

必要輸入有三項：新 GAP YAML、`phonon/ground_truth.yaml`，以及它所需的 `phonon/reference_dft/FORCE_CONSTANTS`。只複製 DFT YAML 不足以重建 DFT 曲線。

```bash
python phonon/compare_phonons.py \
  --gap-yaml phonon/output_reproduction_4x4/csc_ver_reproduced_4x4.yaml \
  --dft-yaml phonon/ground_truth.yaml \
  --dft-force-constants phonon/reference_dft/FORCE_CONSTANTS \
  --output-dir phonon/output_dft_gap_comparison
```

預期輸出：

```text
phonon/output_dft_gap_comparison/
├── dft_gap_phonon_comparison.png
├── dft_gap_bands_meV.npz
└── comparison_metrics.json
```

腳本會在計算差值前確認兩者都是 4×4×4、Fe/Se 數量與順序一致、q-points 完全相同，並統一用 VASP→THz factor 後轉成 meV。路徑為 Γ–X–M–Γ–Z–R–A–Z，每段 100 點；連接點在相鄰兩段各保留一次，因此陣列是 700×12。

| 指標 | 結果 |
| --- | ---: |
| 逐排序分支 MAE | 1.62477 meV |
| 逐排序分支 RMSE | 2.11048 meV |
| 最大絕對差 | 6.17267 meV |
| 最大差位置 | Γ，zero-based branch 9；GAP−DFT = −6.17267 meV |
| 新 GAP 對歷史 GAP 最大差 | 2.68963×10⁻⁶ meV |

新圖與歷史 `comparison_ground_truth_csc.png` 的曲線形狀一致；歷史圖沒有保存 band 數據，因此以保存的 DFT force constants 和歷史 GAP YAML 重新計算作數值核對。舊圖下方程式實際畫的是 `csc−DFT`，但文字曾標為 `DFT−csc`；新圖明確定義為 `GAP−DFT`。

這個 MAE/RMSE 是每個 q-point 依升頻排序後的 branch index 直接相比。簡併點、能帶交叉或 avoided crossing 附近，同一 index 不一定代表相同本徵向量；若要做嚴格模態對應，還需要 eigenvector overlap，這裡沒有假裝已完成該分析。另外 DFT 與 GAP 的晶胞並不完全相同：最大晶格分量差 `0.16924 Å`，最大 wrapped fractional-coordinate 差 `0.007742`，所以本圖是 pre-test 模型比較，不是同一幾何上的純 force-model 誤差。

常見錯誤：

- 找不到 `FORCE_CONSTANTS`：DFT YAML 不含足以獨立重建曲線的力常數；兩者要一起提供。
- branch shape 不是 700×12：檢查是否用了相同四原子 cell、路徑與每段 100 點。
- 頻率整體相差約 4.1357 倍：THz 與 meV 混用；腳本統一在最後乘 `4.135667696 meV/THz`。
- 圖的差值正負和歷史圖相反：先讀 y 軸定義；本教學一律用 `GAP−DFT`。

歷史圖保留作 provenance：

![歷史 DFT/GAP 聲子比較](results/phonon_comparison_historical.png)

![歷史振動熱力學結果](results/thermal_properties_historical.png)

## 第 4 關：從 74 筆資料重新訓練

### 4.1 先理解這次訓練包含什麼

唯一訓練輸入是 `data/csc_data_74.xyz`，SHA-256 為
`809cd88d5657dbd073e0131d67b6b0379831d8f4a9be967c9abb21b882cdb1b0`。它有 74 frames、每筆 Fe16Se16／32 atoms，以及 74 個 finite total-energy labels；沒有 force 或 virial label。74 筆中只有 59 個不同幾何，frames 33–48 的重複會保留，也等於讓該幾何在 loss 中重複出現。這是歷史 provenance，不在教學重訓時私自去重。

`training/train_gap.sh` 由 `model/csc_ver.xml` 的 `<command_line>` 還原。自動逐項比對已確認：除了 `at_file` 改指向上述 repository 內 XYZ、`gp_file` 改到 `training/output/`，其餘參數與順序完全相同：

```text
energy_parameter_name=energy
force_parameter_name=forces
stress_parameter_name=virial
do_copy_at_file=F
sparse_separate_file=T
default_sigma={0.002 0.0 0.0 0.0}
e0_method=average
gap={
  distance_2b cutoff=3.5 delta=1.0 covariance_type=ard_se
              theta_uniform=1.0 sparse_method=cur_points
              add_species=T n_sparse=50
  :
  angle_3b    cutoff=3.5 delta=0.7 covariance_type=ard_se
              theta_fac=1.0 sparse_method=cur_points
              add_species=T n_sparse=200
}
```

參數的直觀意義：

- `energy_parameter_name=energy` 指定 XYZ 中的 total-energy label。force／virial 名稱雖保留於歷史指令，但資料沒有這兩類 labels，所以本次仍是 **energy-only** fitting；新模型的 forces 是能量模型的解析微分，不是對 force labels 擬合。
- `default_sigma={0.002 0.0 0.0 0.0}` 保留歷史 regularisation 設定；第一項是 energy noise scale。其餘分量不會憑空產生不存在的 labels。
- `e0_method=average` 由資料平均估計 atomic baseline。所有 frames 都是固定 Fe16Se16，不能從這組資料獨立識別 Fe 與 Se 各自的 isolated-atom energy。
- `distance_2b` 是 3.5 Å cutoff 的二體距離 descriptor；`angle_3b` 是同 cutoff 的三體角度 descriptor。`delta` 控制 kernel amplitude，`theta_*` 控制 length scale。
- `sparse_method=cur_points` 從所有 local environments 選 sparse representatives；`n_sparse=50/200` 分別是二體／三體每個 species channel 的目標上限。`add_species=T` 會拆成不同 species channels；歷史模型因此引用 9 個 SparseX。
- `sparse_separate_file=T` 將 sparse coordinates 寫在 XML 旁的獨立檔案；移動模型時必須連同它們一起移動。
- `do_copy_at_file=F` 表示不把整份 74-frame XYZ 內嵌進 XML。

### 4.2 環境與安全 preflight

本機已驗證的 training binary：

```text
gap_fit    QUIP v0.10.2-dirty, linux_x86_64_gfortran
compiled   2026-02-23 15:27:34
SHA-256    48427389f82adb94fa6257dec0e3a45fd54b926077f99c046c14304a219b0bb1
Python     3.10.19（只供後續驗證）
NumPy      1.26.4
ASE        3.27/3.28 系列
f90wrap    0.3.0
```

先執行不訓練的預檢：

```bash
command -v gap_fit
bash -n training/train_gap.sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  bash training/train_gap.sh --check-only
```

預期最後一行為：

```text
PASS: training preflight only; gap_fit was not started.
```

preflight 會確認：`gap_fit` 可執行且動態函式庫齊全、輸入 SHA-256 是指定的 74-frame 檔、`training/output/` 不存在或為空，並印出唯一的輸入與輸出絕對路徑。它不建立 output，也不呼叫 `gap_fit`。

這台機器有一個重要的 MPI 相容性陷阱：`gap_fit` 的 RPATH 固定連到 atom_sim conda environment 的 Open MPI 4.1.6，但一般 PATH 上的 `mpirun` 是 Open MPI 5.0.2。不要混用它們。這個小型訓練直接啟動一個 `gap_fit` process 即可，不使用 `mpirun`。Python/quippy 驗證也應使用和 QUIP build 相容的 atom_sim environment。

常見 preflight 錯誤：

- `gap_fit not found`：載入正確 QUIP environment，或設定 `GAP_FIT_BIN=/absolute/path/to/gap_fit`。
- `training-data SHA-256 mismatch`：資料不是保存的 74-frame 版本；不要改指向上一層 440-frame 資料。
- `non-empty output directory`：上一次可能已完成或留下部分輸出；把整個 `training/output/` 改名保存，不要混合兩次 run。
- `shared-library dependencies` 顯示 `not found`：QUIP binary 和目前 compiler/MPI runtime 不相容，先修正 environment，不要硬跑。

### 4.3 正式訓練

取得資源核准後，請在前述 `U0J0_pretest/` 工作目錄執行：

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
bash training/train_gap.sh
```

本次正式資源量測使用下列受限版本；`time` 的檔案先放 `/tmp`，避免腳本把它誤認為既有 output：

```bash
resource_log=$(mktemp /tmp/u0j0_gap_fit_resource.XXXXXX)
timeout 600s bash -c \
  'ulimit -v 2097152; exec /usr/bin/time -v -o "$1" bash training/train_gap.sh' \
  _ "$resource_log"
mv "$resource_log" training/output/resource_usage.txt
```

腳本只允許全新的空 output。`train_gap.sh` 會建立 metadata、log、新 XML 與 SparseX；驗證腳本另寫 JSON。`resource_usage*.txt` 是用 `/usr/bin/time` 包住命令時的量測紀錄，`retraining_report.json` 則是本次測試摘要，並非 `gap_fit` 自動產物：

```text
training/output/run_metadata.txt
training/output/train_gap.log
training/output/csc_ver_retrained.xml
training/output/csc_ver_retrained.xml.sparseX.*
training/output/resource_usage.txt
training/output/validation_resource_usage.txt
training/output/validation_metrics.json
training/output/retraining_report.json
```

`model/csc_ver.xml` 與原始 9 個 SparseX 不在輸出路徑內，也受 `checksums.sha256` 監控。若 output 中已有任何檔案，腳本就拒絕執行。失敗的 run 可能留下 partial XML、SparseX 或 log；保留它們除錯並把整個目錄改名，不能直接混著重跑。

此資料只有 74 個 energy observations、2,368 個 atomic environments。2026-10-10 實測限制為 **1 CPU、2 GiB、600 秒**，直接啟動一個 process、不用 mpirun；訓練成功耗時 7.16 秒、maximum RSS 63,024 KiB、無 swap、exit code 0。QUIP 自己估計 linear-system peak 約 46 MB，實際 RSS 仍以 `/usr/bin/time -v` 為準。

Log 中有三個預期 warning：Se–Se 二體 channel 只有 3 個可用點，所以 sparse 數由 50 降為 3；兩個稀少 Se-centered 三體 channel 分別只有 7、8 點，所以由 200 降為 7、8。這正好對應歷史模型的 SparseX 大小，不是 fitting failure，也沒有為了消除 warning 改參數。

### 4.4 新模型驗證

訓練成功後先跑 74-frame 行為檢查：

```bash
PYTHONPATH="$QUIP_PYTHON_BUILD" \
  python training/validate_retrained_model.py
```

它會同時載入歷史與新模型，確認全部 74 筆 energy 及 `(74,32,3)` forces 都是 finite，並輸出：

```text
training/output/validation_metrics.json
```

報告包含新模型對 74 個 energy labels 的 MAE/RMSE/max、新舊模型 energy 差、新舊模型 force-component 差，以及 frame 0 重複推論的一致性。這些 energy residual 是 **in-sample training error**，不能當泛化誤差；資料完全沒有 force labels，因此 force 只能做新舊行為比較，不能宣稱對 DFT force 的 accuracy。

歷史模型的低成本 baseline 已量測：74-frame total-energy MAE `5.665×10⁻⁵ eV`、RMSE `1.157×10⁻⁴ eV`、最大差 `5.259×10⁻⁴ eV`，所有 energy／forces finite。新模型不必和舊 XML 逐 byte 相同；應記錄 QUIP binary SHA、training-data SHA、log 與 SparseX，確認 energy residual 在合理量級，再誠實報告新舊 force 差異。若差異顯著，先檢查 QUIP/BLAS 版本、random seed 與 sparse selection，而不是私自改參數讓結果變好看。

2026-10-10 的實際驗證結果：

| 指標 | MAE | RMSE | 最大絕對差 |
| --- | ---: | ---: | ---: |
| 新模型 − training energy label (eV/config) | 5.688×10⁻⁵ | 1.163×10⁻⁴ | 5.286×10⁻⁴ |
| 新模型 − training energy label (eV/atom) | 1.778×10⁻⁶ | 3.635×10⁻⁶ | 1.652×10⁻⁵ |
| 新模型 − 歷史模型 energy (eV/config) | 2.603×10⁻⁷ | 7.528×10⁻⁷ | 4.171×10⁻⁶ |
| 新模型 − 歷史模型 force components (eV/Å) | 9.983×10⁻⁵ | 3.487×10⁻⁴ | 3.428×10⁻³ |

新舊模型的 74×32×3 forces 與全部 energies 都是 finite；frame 0 重複推論的 energy 與最大 force-component 差皆為 0。新 XML 可由 quippy 載入，引用的 9 個 SparseX 全部存在且 XML 內嵌 MD5 全數吻合。驗證耗時 4.38 秒、maximum RSS 110,480 KiB、exit code 0。

## 第 5 關：使用自己訓練的 GAP 重新計算聲子

必要輸入是第 4 關產生的 `training/output/csc_ver_retrained.xml`、它引用的 9 個新 SparseX，以及保存歷史 relaxed unit cell／位移資料的 `phonon/csc_ver.yaml`。腳本不做 relaxation，會先核對 4×4×4、0.01 Å 位移與歷史 dataset 完全一致，再計算 perfect-cell 背景力、四個 displaced supercells、compact force constants 和相同 q-path：

```bash
python phonon/reproduce_historical_4x4.py \
  --model training/output/csc_ver_retrained.xml \
  --output-dir phonon/output_retrained_model_4x4
```

預期輸出：

```text
phonon/output_retrained_model_4x4/
├── csc_ver_reproduced_4x4.yaml
├── phonon_reproduced_4x4.png
├── history_vs_reproduced.png
└── reproduction_metrics.json
```

2026-10-10 實測使用 1 CPU、2 GiB 上限與 300 秒 timeout：

| 指標 | 結果 |
| --- | ---: |
| 位移結構／原子數 | 4／256 atoms |
| 背景力最大分量 | 4.854×10⁻⁴ eV/Å |
| 新舊聲子 MAE | 0.003869 meV |
| 新舊聲子 RMSE | 0.004713 meV |
| 新舊聲子最大差 | 0.012616 meV |
| 歷史／重訓模型最低頻率 | −1.636×10⁻⁶／−9.605×10⁻⁷ meV |
| 低於 −0.1 meV 的頻率值 | 0／0 |
| Wall time／maximum RSS | 19.84 秒／716,104 KiB |

負的數值只在約 `10⁻⁶ meV` 的 acoustic numerical zero，沒有實質虛頻。新舊曲線在圖上重合；可重生的 16.5 MB YAML 不納入 Git，數值報告與比較圖保存於 `results/retrained_phonon_metrics.json` 和 `results/retrained_vs_historical_phonons.png`。

![歷史 GAP 與重訓 GAP 的聲子比較](results/retrained_vs_historical_phonons.png)

物理意義是檢查「相同資料與設定重新訓練」是否保持二階力常數和聲子行為，而不是要求 XML 或 SparseX 逐 byte 相同。常見錯誤包括只複製 XML、使用 POSCAR 取代歷史 YAML cell、對既有 output 覆寫，以及把 `10⁻⁶ meV` 的數值零誤判為虛頻。若差異明顯，應如實記錄 QUIP/BLAS、random seed、SparseX 與 training log，不可私自調參後只保留較好結果。

## 資源預估與執行順序

工作狀態與建議順序：

1. 保存模型的 2×2×2、skip-relax Phonopy smoke test：**已完成**；1 CPU，15.96 秒，maximum RSS 169.97 MiB。
2. 歷史 relaxed cell 的 4×4×4 重算（不含 relaxation）：**已完成**；1 CPU，25.59 秒，maximum RSS 約 700 MiB。
3. YAML thermal 重算：**已完成**；1 CPU，42.70 秒，maximum RSS 639,028 KiB（約 624 MiB）。
4. DFT／GAP comparison：**已完成**；1 CPU，24.27 秒，maximum RSS 622,212 KiB（約 608 MiB）。
5. 74-frame GAP retraining：**已完成**；單一 process、1 CPU、7.16 秒、maximum RSS 63,024 KiB、exit code 0。74-frame validation 另耗時 4.38 秒、maximum RSS 110,480 KiB。
6. 重訓模型的 4×4×4 聲子：**已完成**；1 CPU、19.84 秒、maximum RSS 716,104 KiB，300 秒內正常結束。

先完成既有模型的 Phonopy，再開始重新訓練，避免同時引入模型與流程兩種變因。

## 結果判讀

- 高溫 `C_V` 趨近 3`k_B`/atom 是諧振三維固體的物理一致性檢查，不等於模型已定量準確。
- 虛頻要檢查平衡結構、位移量、supercell、背景力、聲學和規則與模型品質。
- DFT/GAP 比較必須使用一致的 q-path、單位、原子排序與可比結構。此處歷史 GAP 與 DFT 結構並非完全相同，圖只適合作為 pre-test。
- 74 筆中有重複幾何且沒有獨立 force label；若要評估泛化能力，需另建獨立測試集，不能只看訓練 frame 0。

## 不納入 repository 的檔案

不得加入 `POTCAR`、私鑰、token、憑證、`WAVECAR`、`CHGCAR` 或與教學無關的大型計算檔。VASP 與 DFT+gRISB 的新計算不屬於本次整理範圍。
