# Si｜MACE energy-only 與 GAP 分析範例

此目錄包含兩類**不同模型框架**的範例，請勿將其視為已串接完成的單一工作流程。

| 檔案 | 用途 | 模型 |
| --- | --- | --- |
| [MACE/](MACE/) | Energy-only 訓練指令與 foundation-model 微調示範 | **MACE** |
| [MD.py](MD.py) | 使用 ASE Langevin thermostat 執行 NVT MD（目前設定 3×3×3 conventional Si cell，216 atoms） | **GAP／QUIP** |
| [RMSE.py](RMSE.py) | 比較 DFT 參考與 GAP 預測的能量、力、應力，並繪製 parity plot | **GAP／QUIP** |

`MD.py` 預設需要 `GAP_Si_Final.xml`，`RMSE.py` 需要 `GAP_Si_Final.xml` 與 `si_training_easy.xyz`；這些輸入並未全部包含在儲存庫。若要做**真正的 energy-only 驗證**，需確認 RMSE 用的參考資料是否具有 force/stress 標記，並對缺失標記的情況調整程式。

MACE 的訓練模型不能直接輸入使用 `quippy.potential.Potential` 的程式；必須改用適合 MACE 的 ASE calculator。
