# THLee Lab｜Energy-only 機器學習原子間位能（MLIP）

本儲存庫整理國立中正大學 THLee Lab 使用**僅含能量標記（energy-only）**的參考資料，訓練及分析機器學習原子間位能（Machine-Learned Interatomic Potentials, MLIPs）之研究範例。包含 **FeSe**（VASP／DFT+gRISB、GAP／QUIP、Phonopy）及 **Si**（MACE 訓練範例、GAP 分析腳本）。

> **專案狀態：研究用範例，持續整理中。** U=J=0 的 74-frame GAP→Phonopy 教材已附完整資料、歷史模型與可執行腳本，並完成端到端驗證；儲存庫內其他範例仍可能依賴實驗室環境或外部 DFT 結果。本專案中的不同計算方法及圖稿需按各自設定判讀。

## 研究概念

一般 MLIP 可使用能量、力、應力等參考資料。本研究著重探討：**只利用總能量訓練的位能，能否描述結構弛豫、聲子與振動熱力學性質？**

對於可微分的位能模型，原子受力可由預測能量對原子位置求導得到：

$$\mathbf F_i=-\nabla_{\mathbf R_i}E_{\mathrm{MLIP}}.$$

因此「energy-only 訓練」**不代表**後續聲子計算不使用力；其差別在於訓練時不直接採用 DFT 力／應力作為監督標記。

## 目錄導航

| 路徑 | 主要內容 |
| --- | --- |
| [FeSe/VASP/](FeSe/VASP/) | VASP／DFT+gRISB 參考資料、ASE 結構生成、GAP 訓練、聲子與熱性質工作流程 |
| [FeSe/VASP/ASE/](FeSe/VASP/ASE/) | strain、rattle、shear、phonon displacement、SCF/CSC 能量擷取 |
| [FeSe/VASP/QUIP/](FeSe/VASP/QUIP/) | GAP／QUIP 訓練指令、能量資料集與結構弛豫 |
| [FeSe/VASP/QUIP/U0J0_pretest/](FeSe/VASP/QUIP/U0J0_pretest/) | 已驗證的 74-frame energy-only GAP、4×4×4 Phonopy、熱性質與 DFT 比較五關教材 |
| [FeSe/VASP/phonopy/](FeSe/VASP/phonopy/) | 聲子頻譜、主動學習、比較及熱力學 |
| [Si/](Si/) | Si 分子動力學、RMSE、MACE 訓練範例 |

**目錄結構備註：** FeSe 原本的資料已集中移至 `FeSe/VASP/`；各子目錄中既有相對執行路徑原則上保留，但由舊路徑啟動的外部腳本需自行更新。

## FeSe 工作流程

~~~mermaid
flowchart LR
    A["ASE 生成應變／位移結構"] --> B["VASP / DFT(+gRISB) 計算能量"]
    B --> C["擷取 extended XYZ"]
    C --> D["QUIP / GAP energy-only 訓練"]
    D --> E["結構弛豫與 Phonopy 聲子計算"]
    E --> F["與參考結果比較"]
    F --> G["選取高誤差模態、追加資料"]
    G --> B
~~~

資料夾中提供 `4×4×2` FeSe 超胞之 extended XYZ 範例。已直接統計目前 `FeSe/VASP/QUIP/energy_only_dataset.xyz`，共有 **440 筆構型（每筆 128 顆原子，且皆具 energy 標記）**。這是 GitHub 現有資料集的數量，**不是**下方兩張結果圖使用的 74 筆資料。更詳細的輸入、參數與限制請參閱 [FeSe/VASP/README.md](FeSe/VASP/README.md)。

## FeSe 初步測試：U = J = 0，74 筆訓練紀錄

**給新進學弟的實作入口：** [FeSe 74 筆 energy-only GAP → Phonopy 入門教學](FeSe/VASP/QUIP/U0J0_pretest/)。教材依序涵蓋既有模型聲子、振動熱力學、DFT/GAP 比較、74-frame 重訓與新模型聲子；原始 XYZ、歷史 XML＋9 個 SparseX、Phonopy／DFT 輸入與可執行腳本均已納入並通過低成本端到端測試。

這兩張圖為 **pre-test（初步可行性測試）**，使用 **74 筆 Charge-Self-Consistent（CSC，電荷自洽）計算的 FeSe 總能量紀錄（59 個不同幾何構型）**作為訓練標記，透過 **QUIP/GAP 進行 energy-only 訓練**，再利用模型預測力與 **Phonopy** 求得聲子及振動熱力學性質。**CSC 是訓練能量的來源，而不是另一種 MLIP。**

本次測試設定為 **U = 0、J = 0**，尚未加入有限 Hubbard U 和 Hund J 所代表的局域強關聯修正。因此這些結果僅能展示本工作流程在此基準條件下的可行性，**不能當成已描述 FeSe 強關聯效應的證據**。

### 聲子色散：DFT 基準與 CSC-energy-trained GAP

![FeSe U=J=0 pre-test 聲子色散](FeSe/VASP/QUIP/U0J0_pretest/results/phonon_comparison_historical.png)

圖中**藍色虛線（DFT）**是參考聲子結果，**紅色實線（圖例 CSC）**是以 CSC 的 74 筆總能量訓練之 **GAP** 所預測的聲子色散，經 **Phonopy** 計算。歷史圖的差值標籤與實際程式正負號不一致；新教材明確採 `GAP−DFT`。整體色散趨勢相近，但部分聲子分支仍有數 meV 級差異；這不是獨立驗證集精度，且兩曲線使用的 relaxed geometry 不完全相同。

### Phonon DOS 與熱力學性質

![FeSe U=J=0 pre-test 振動熱力學性質](FeSe/VASP/QUIP/U0J0_pretest/results/thermal_properties_historical.png)

圖中呈現以該次 74 筆 CSC 能量資料訓練之 GAP，配合 Phonopy 得到的聲子 DOS、定容熱容、熵及 Helmholtz 自由能。熱容在高溫趨近 **3 k_B/atom**（Dulong–Petit 極限），可作為物理一致性檢查，**不等於**已與 DFT 或實驗完成定量比對。

> **重現性提醒：** U0J0 教材使用獨立保存的 `csc_data_74.xyz`（74 筆、每筆 32 原子，59 個不同幾何）與對應模型。上一層的 `energy_only_dataset.xyz` 是另一組 **440 筆、每筆 128 原子**的資料；兩者不可混用。74-frame 的 energy MAE/RMSE 是訓練集殘差，不是獨立驗證精度。

## Si 相關程式

[Si/MACE/](Si/MACE/) 提供 MACE 的 energy-only 權重設定與 foundation model 微調指令；[Si/MD.py](Si/MD.py) 及 [Si/RMSE.py](Si/RMSE.py) 使用的則是 **GAP／QUIP**。這些腳本是分開的範例，不能把 MACE 模型直接當作 GAP XML 使用。Si 的部分資料／訓練模型未隨 repo 一起提供。

## 執行環境與重現性

依任務可能需要 Python 3、NumPy、Matplotlib、[ASE](https://ase-lib.org/)、[Phonopy](https://phonopy.github.io/phonopy/)、[QUIP／quippy](https://github.com/libAtoms/QUIP)、[MACE](https://github.com/ACEsuit/mace)，以及產生參考資料時使用的 VASP、gRISB 與 MPI 環境。

- `create_xyz.py` 對 `scf/`、`csc/` 資料夾及特定收斂訊息有格式假設。
- 儲存庫內較早的範例仍可能使用硬編碼模型檔名、POSCAR/CONTCAR 或本機路徑；U0J0 教材已改用 repository 內相對路徑與可指定的 output 目錄。
- 僅提交程式與少量示範資料，不代表訓練權重、所有 DFT 輸出或軟體授權均已提供。
- U0J0 的代表性圖像、輸入與運算條件已核對；其他研究範例仍需依各子目錄 README 判讀。

## 授權與引用

本儲存庫目前未附獨立 LICENSE；請勿直接視為已授權任何再散布或商用用途。使用 ASE、QUIP/GAP、Phonopy、MACE、VASP 或 gRISB 時請遵循各自授權及原始論文的引用要求。
