#!/usr/bin/env bash
set -euo pipefail

# Reconstructed verbatim from <command_line> in model/csc_ver.xml.
# Only at_file and gp_file were changed to repository-relative paths.

if [[ ${1-} == "--check-only" ]]; then
  check_only=true
  shift
else
  check_only=false
fi
if (( $# != 0 )); then
  echo "usage: $0 [--check-only]" >&2
  exit 64
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
tutorial_root=$(cd -- "$script_dir/.." && pwd)
data_file="$tutorial_root/data/csc_data_74.xyz"
output_dir="$script_dir/output"
output_xml="$output_dir/csc_ver_retrained.xml"
gap_fit_bin=${GAP_FIT_BIN:-gap_fit}
expected_data_sha256=809cd88d5657dbd073e0131d67b6b0379831d8f4a9be967c9abb21b882cdb1b0

if ! command -v "$gap_fit_bin" >/dev/null 2>&1; then
  echo "error: gap_fit not found: $gap_fit_bin" >&2
  echo "Load QUIP or set GAP_FIT_BIN=/absolute/path/to/gap_fit." >&2
  exit 127
fi

if [[ ! -f "$data_file" ]]; then
  echo "error: training data not found: $data_file" >&2
  exit 2
fi

actual_data_sha256=$(sha256sum "$data_file" | awk '{print $1}')
if [[ "$actual_data_sha256" != "$expected_data_sha256" ]]; then
  echo "error: training-data SHA-256 mismatch" >&2
  echo "expected: $expected_data_sha256" >&2
  echo "actual:   $actual_data_sha256" >&2
  exit 2
fi

if [[ -e "$output_dir" && ! -d "$output_dir" ]]; then
  echo "error: output path exists and is not a directory: $output_dir" >&2
  exit 3
fi
if [[ -d "$output_dir" && -n $(find "$output_dir" -mindepth 1 -print -quit) ]]; then
  echo "error: refusing to use non-empty output directory: $output_dir" >&2
  echo "Move training/output aside before starting a new run." >&2
  exit 3
fi

gap_fit_path=$(command -v "$gap_fit_bin")
if ldd "$gap_fit_path" 2>/dev/null | grep -q 'not found'; then
  echo "error: gap_fit has unresolved shared-library dependencies" >&2
  ldd "$gap_fit_path" >&2
  exit 4
fi

export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-1}

echo "Training data: $data_file"
echo "Data SHA256:  $actual_data_sha256"
echo "New model:    $output_xml"
echo "gap_fit:      $gap_fit_path"
echo "Threads:      OMP=$OMP_NUM_THREADS OPENBLAS=$OPENBLAS_NUM_THREADS"
echo "Launch mode:  one direct gap_fit process (no mpirun)"
echo "Historical model/model SparseX files will not be modified."

if [[ "$check_only" == true ]]; then
  echo "PASS: training preflight only; gap_fit was not started."
  exit 0
fi

mkdir -p "$output_dir"
{
  echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "hostname=$(hostname)"
  echo "gap_fit=$gap_fit_path"
  echo "gap_fit_sha256=$(sha256sum "$gap_fit_path" | awk '{print $1}')"
  echo "training_data=$data_file"
  echo "training_data_sha256=$actual_data_sha256"
  echo "OMP_NUM_THREADS=$OMP_NUM_THREADS"
  echo "OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
} > "$output_dir/run_metadata.txt"

"$gap_fit_path" \
  "energy_parameter_name=energy" \
  "force_parameter_name=forces" \
  "stress_parameter_name=virial" \
  "do_copy_at_file=F" \
  "sparse_separate_file=T" \
  "gp_file=$output_xml" \
  "at_file=$data_file" \
  "default_sigma={0.002 0.0 0.0 0.0}" \
  "e0_method=average" \
  "gap={distance_2b cutoff=3.5 delta=1.0 covariance_type=ard_se theta_uniform=1.0 sparse_method=cur_points add_species=T n_sparse=50 : angle_3b cutoff=3.5 delta=0.7 covariance_type=ard_se theta_fac=1.0 sparse_method=cur_points add_species=T n_sparse=200}" \
  2>&1 | tee "$output_dir/train_gap.log"

echo "Created $output_xml and its separate SparseX files."
