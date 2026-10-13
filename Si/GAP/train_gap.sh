#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python_bin=${PYTHON_BIN:-python3}
gap_fit_bin=${GAP_FIT_BIN:-gap_fit}
mpirun_bin=${MPIRUN_BIN:-mpirun}
nprocs=${NPROCS:-4}
input_xyz=${INPUT_XYZ:-"$script_dir/../train_smart.xyz"}
run_dir=${RUN_DIR:-"$script_dir/run"}

mkdir -p "$run_dir"
"$python_bin" "$script_dir/prepare_energy_only.py" \
  --input "$input_xyz" \
  --output "$run_dir/si_train_energy_only.xyz"

cd "$run_dir"

gap_descriptor='{ \
        distance_2b \
            cutoff=5.0 \
            delta=1.0 \
            covariance_type=ard_se \
            theta_uniform=1.0 \
            sparse_method=uniform \
            add_species=T \
            n_sparse=50 \
        : \
        soap \
            cutoff=5.0 \
            delta=1.0 \
            l_max=6 \
            n_max=8 \
            atom_sigma=0.5 \
            n_sparse=1000 \
            covariance_type=dot_product \
            sparse_method=cur_points \
            zeta=4 \
            add_species=T \
    }'

gap_args=(
  "at_file=si_train_energy_only.xyz"
  "gp_file=GAP_Si_EnergyOnly.xml"
  "energy_parameter_name=energy"
  "e0_method=average"
  "default_sigma={0.002 0.0 0.0 0.0}"
  "gap=$gap_descriptor"
  "do_copy_at_file=F"
  "sparse_separate_file=T"
)

if [[ "$nprocs" == "1" ]]; then
  "$gap_fit_bin" "${gap_args[@]}" 2>&1 | tee GAP_Si_EnergyOnly.log
else
  "$mpirun_bin" -np "$nprocs" "$gap_fit_bin" "${gap_args[@]}" \
    2>&1 | tee GAP_Si_EnergyOnly.log
fi
