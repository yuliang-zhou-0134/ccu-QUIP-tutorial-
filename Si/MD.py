# Si_MD_Evolution_NVT.py (熱浴版本)
import os
import numpy as np
from ase import units
from ase.build import bulk
from ase.io import Trajectory
from quippy.potential import Potential
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
# 【修改 1】引入 Langevin 溫控器
from ase.md.langevin import Langevin 


# 1. 載入模型
xml_filename = "GAP_Si_Final.xml"
calc = Potential(param_filename=xml_filename)

# 解決 QUIProcs 寫入 Trajectory 的相容性問題
calc.name = 'quip'

# 1. 設定單機多執行緒 (讓這一支程式吃滿 16 核)
os.environ["OMP_NUM_THREADS"] = "16"
os.environ["MKL_NUM_THREADS"] = "16"
os.environ["MPI_NUM_THREADS"] = "1"

# 2. 建立矽結構 (216 顆原子：8-atom conventional cell × 3×3×3)
atoms = bulk('Si', 'diamond', a=5.5063,cubic=True) * (3, 3, 3)

# 3. 設定計算器
atoms.calc = calc

# 4. 初始化溫度 (300K)
TARGET_TEMP = 300 # Kelvin
print(f"Initializing velocities at {TARGET_TEMP}K...")
MaxwellBoltzmannDistribution(atoms, temperature_K=TARGET_TEMP)

# 5. 設定 MD 動力學引擎
# 【修改 2】將 VelocityVerlet (NVE) 替換為 Langevin (NVT)
# friction: 摩擦係數，控制溫控器對系統的干預程度 (0.002 ps^-1 是固體常用的鬆弛時間)
# temperature: 目標溫度 (必須使用 ase.units.K)
dyn = Langevin(atoms, 
               timestep=1.0 * units.fs, 
               temperature_K=TARGET_TEMP, 
               friction=0.02) 

# 6. 設定輸出軌跡檔 (.traj)
traj = Trajectory('si_md_NVT.traj', 'w', atoms)
# 設為每 20 步存檔一次，減少檔案大小
dyn.attach(traj.write, interval=20) 

# 7. 設定螢幕輸出 (監控進度)
def printenergy(a=atoms):
    epot = a.get_potential_energy() / len(a)
    ekin = a.get_kinetic_energy() / len(a)
    print(f"Step: {dyn.nsteps:5d} | Epot: {epot:.3f}eV | Ekin: {ekin:.3f}eV | Temp: {a.get_temperature():.1f}K", flush=True)

# 每 1 步顯示一次狀態
dyn.attach(printenergy, interval=1)

# 8. 開始跑 (跑 20,000 步，約 20 ps)
N_STEPS = 20000 
print(f"Starting Molecular Dynamics simulation in NVT ensemble ({N_STEPS} steps)...")
dyn.run(N_STEPS)

print("MD Finished! Output saved to si_md_NVT.traj")
