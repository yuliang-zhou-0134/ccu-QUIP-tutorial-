這是我之前計算FeSe所使用的一些有用的程式碼
目前流程是ASE生成初始結構(ASE資料夾)-->VASP計算能量-->QUIP建構位能面(QUIP資料夾)-->利用phonopy計算聲子圖(phonopy資料夾)-->如果和預期不同，主動學習(phonopy資料夾)-->利用phonopy計算聲子圖和簡偕熱特性(phonopy資料夾)
