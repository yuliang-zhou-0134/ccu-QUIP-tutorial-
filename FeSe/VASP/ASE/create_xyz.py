import argparse
import re
from pathlib import Path

import numpy as np

SKIP_NAMES = {"Fe", "Se", "train_QUIP_data"}

GRISB_PATTERN = re.compile(
    r"iter_grisb=\s*25\s+n_iter_grisb=\s*25\s+iteration_offset=\s*0"
)
COMPLEX_PATTERN = re.compile(
    r"([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*([+-]\s*\d+\.?\d*(?:[eE][+-]?\d+)?)\s*j"
)
FLOAT_PATTERN = re.compile(r"[+-]?\d+\.\d+(?:[eE][+-]?\d+)?")


# --------------------------------------------------------------------------
# POSCAR 解析
# --------------------------------------------------------------------------
def parse_poscar(path):
    """回傳 (symbols, cart_positions(Nx3), lattice(3x3))"""
    with open(path, "r", errors="ignore") as f:
        lines = [l.rstrip("\n") for l in f if l.strip() != "" or True]

    # 去掉尾端多餘空行但保留索引正確性較麻煩，改用簡單方式：直接照原始行號讀
    with open(path, "r", errors="ignore") as f:
        raw = [l.rstrip("\n") for l in f]

    scale = float(raw[1].split()[0])
    lattice = np.array([[float(x) for x in raw[i].split()[:3]] for i in (2, 3, 4)])

    if scale < 0:
        vol = abs(np.linalg.det(lattice))
        factor = (abs(scale) / vol) ** (1.0 / 3.0)
        lattice = lattice * factor
        cart_scale = 1.0  # 此時 cartesian 座標本身不再額外乘 scale
    else:
        lattice = lattice * scale
        cart_scale = scale

    idx = 5
    tokens = raw[idx].split()
    if tokens and all(re.match(r"^[A-Za-z]+$", t) for t in tokens):
        symbols_line = tokens
        idx += 1
        counts = [int(c) for c in raw[idx].split()]
        idx += 1
    else:
        # VASP4 舊格式，沒有元素符號列
        counts = [int(c) for c in tokens]
        symbols_line = [f"X{i+1}" for i in range(len(counts))]
        idx += 1

    mode_line = raw[idx].strip()
    if mode_line[:1].upper() == "S":  # Selective dynamics
        idx += 1
        mode_line = raw[idx].strip()
    coord_mode = mode_line[:1].upper()  # 'D'irect 或 'C'/'K'artesian
    idx += 1

    symbols = []
    for sym, cnt in zip(symbols_line, counts):
        symbols += [sym] * cnt
    natoms = sum(counts)

    positions = []
    for i in range(natoms):
        parts = raw[idx + i].split()
        positions.append([float(parts[0]), float(parts[1]), float(parts[2])])
    positions = np.array(positions)

    if coord_mode == "D":
        cart = positions @ lattice
    else:
        cart = positions * cart_scale

    return symbols, cart, lattice


# --------------------------------------------------------------------------
# 能量擷取
# --------------------------------------------------------------------------
def extract_real_part(text):
    """從 'total energy' 那行擷取複數的實部；找不到複數格式就退回抓一般浮點數。"""
    m = COMPLEX_PATTERN.search(text)
    if m:
        return float(m.group(1))
    m2 = FLOAT_PATTERN.search(text)
    if m2:
        return float(m2.group(0))
    return None


def get_last_total_energy(nohup_path):
    last = None
    with open(nohup_path, "r", errors="ignore") as f:
        for line in f:
            if "total energy" in line:
                val = extract_real_part(line)
                if val is not None:
                    last = val
    return last


def get_last_free_energy(outcar_path):
    last = None
    pattern = re.compile(r"free\s+energy.*?=\s*([+-]?\d+\.\d+(?:[eE][+-]?\d+)?)")
    with open(outcar_path, "r", errors="ignore") as f:
        for line in f:
            if "free" in line and "energy" in line:
                m = pattern.search(line)
                if m:
                    last = float(m.group(1))
    return last


# --------------------------------------------------------------------------
# 成功與否判斷
# --------------------------------------------------------------------------
def check_success(csc_dir):
    nohup_path = csc_dir / "nohup.out"
    if not nohup_path.is_file():
        return False, "找不到 nohup.out"
    with open(nohup_path, "r", errors="ignore") as f:
        lines = f.readlines()
    tail_text = "".join(lines[-100:])
    if GRISB_PATTERN.search(tail_text):
        return True, "成功"
    return False, "未收斂 (tail -100 內找不到收斂字串)"


# --------------------------------------------------------------------------
# 資料夾搜尋
# --------------------------------------------------------------------------
def find_calc_dirs(base):
    """回傳一串同時含有 scf/ 與 csc/ 子資料夾的目錄。"""
    result = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name in SKIP_NAMES:
            print(f"[skip] {entry.name} (略過清單內)")
            continue

        if (entry / "scf").is_dir() and (entry / "csc").is_dir():
            # 第一類：0%、1%...、nega_1%...
            result.append(entry)
            continue

        # 第二類：底下是子資料夾，命名可能是 task_*、disp_* 或其他
        # 不寫死前綴，改成掃描所有子資料夾，只要裡面同時有 scf/ 與 csc/ 就算數
        sub_dirs = [p for p in sorted(entry.iterdir()) if p.is_dir()]
        matched = [t for t in sub_dirs if (t / "scf").is_dir() and (t / "csc").is_dir()]

        if matched:
            result.extend(matched)
            continue

        print(f"[warn] {entry.name} 不符合預期結構 (非 scf/csc、底下也沒有含 scf/csc 的子資料夾)，略過")
    return result


# --------------------------------------------------------------------------
# 寫出 extended xyz
# --------------------------------------------------------------------------
def write_xyz_frame(f, symbols, positions, lattice, energy, extra_comment=""):
    n = len(symbols)
    lattice_str = " ".join(f"{v:.8f}" for row in lattice for v in row)
    comment = (
        f'Lattice="{lattice_str}" Properties=species:S:1:pos:R:3 '
        f'energy={energy:.8f} pbc="T T T"'
    )
    if extra_comment:
        comment += f" {extra_comment}"
    f.write(f"{n}\n{comment}\n")
    for sym, pos in zip(symbols, positions):
        f.write(f"{sym} {pos[0]:.8f} {pos[1]:.8f} {pos[2]:.8f}\n")


# --------------------------------------------------------------------------
# 主程式
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base_dir", nargs="?", default=".", help="要掃描的根目錄")
    ap.add_argument("--csc-out", default="csc_data.xyz")
    ap.add_argument("--scf-out", default="scf_data.xyz")
    args = ap.parse_args()

    base = Path(args.base_dir).resolve()
    calc_dirs = find_calc_dirs(base)
    print(f"\n共找到 {len(calc_dirs)} 個計算資料夾 (含 scf/csc)\n")

    # 在開檔前先檢查：不允許兩個輸出指向同一位置，也不覆寫已有 XYZ。
    out_csc = Path(args.csc_out)
    out_scf = Path(args.scf_out)
    if out_csc.resolve() == out_scf.resolve():
        raise ValueError("CSC 與 SCF 輸出路徑不能相同")
    existing_outputs = [
        str(path) for path in (out_csc, out_scf)
        if path.exists() or path.is_symlink()
    ]
    if existing_outputs:
        raise FileExistsError(
            "輸出檔案已存在，為避免覆寫請指定新檔名：" + ", ".join(existing_outputs)
        )

    n_success = 0
    n_fail = 0

    # x 為 exclusive create；即使預檢後路徑被其他程序建立，也不會覆寫。
    with open(out_csc, "x") as csc_f, open(out_scf, "x") as scf_f:
        for d in calc_dirs:
            csc_dir = d / "csc"
            scf_dir = d / "scf"
            rel = d.relative_to(base)

            ok, reason = check_success(csc_dir)
            if not ok:
                print(f"[FAIL] {rel}: {reason}")
                n_fail += 1
                continue

            n_success += 1
            print(f"[OK]   {rel}")

            # ---- csc: total energy ----
            nohup_path = csc_dir / "nohup.out"
            energy_csc = get_last_total_energy(nohup_path)
            poscar_csc = csc_dir / "POSCAR"
            if energy_csc is None:
                print(f"       [warn] csc: 找不到 total energy")
            elif not poscar_csc.is_file():
                print(f"       [warn] csc: 找不到 POSCAR")
            else:
                try:
                    symbols, positions, lattice = parse_poscar(poscar_csc)
                    write_xyz_frame(
                        csc_f, symbols, positions, lattice, energy_csc,
                        extra_comment=f'source="{rel}/csc"'
                    )
                except Exception as e:
                    print(f"       [error] csc POSCAR 解析失敗: {e}")

            # ---- scf: free energy ----
            outcar_path = scf_dir / "OUTCAR"
            energy_scf = get_last_free_energy(outcar_path) if outcar_path.is_file() else None
            poscar_scf = scf_dir / "POSCAR"
            if energy_scf is None:
                print(f"       [warn] scf: 找不到 free energy (OUTCAR)")
            elif not poscar_scf.is_file():
                print(f"       [warn] scf: 找不到 POSCAR")
            else:
                try:
                    symbols, positions, lattice = parse_poscar(poscar_scf)
                    write_xyz_frame(
                        scf_f, symbols, positions, lattice, energy_scf,
                        extra_comment=f'source="{rel}/scf"'
                    )
                except Exception as e:
                    print(f"       [error] scf POSCAR 解析失敗: {e}")

    print(f"\n完成。成功 {n_success} 個，失敗 {n_fail} 個。")
    print(f"輸出檔案：{args.csc_out} , {args.scf_out}")


if __name__ == "__main__":
    main()

