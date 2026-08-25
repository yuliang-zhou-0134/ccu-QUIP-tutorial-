目前只有在colab測試過，沒有用CPU測試訓練的速度，MP0下載指令(在colab執行需要加"!")!wget https://github.com/ACEsuit/mace-mp/releases/download/mace_mp_0/2023-12-03-mace-128-L1_epoch-199.model -O mace_mp.model
r_max看的距離
default_dtype精度
max_num_epochs跑幾次訓練結束
start_swa甚麼時候開始swa(每次訓練完都平均來生成新模型)
energy_weight能量的權重，數字越大越激進
MACE的好處是理論上設定一樣的r_max可以多看到一倍的距離
MP0表示預訓練模型，指的是模型作者先給一堆不同材料、PBE來先訓練，給予新數據-->微調
