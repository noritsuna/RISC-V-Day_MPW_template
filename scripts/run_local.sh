#!/usr/bin/env bash
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# RISC-V Day MPW
# LICENSE: Apache License Version 2.0, January 2004
# http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# Run the same Precheck / DRC / LVS flow as GitHub Actions on a local PDK.
#
# Usage: scripts/run_local.sh [PDK_DIR]   (default: ../gf180mcuD)
# Results are written to ./run/
set -euo pipefail

cd "$(dirname "$0")/.."
PDK_DIR="$(realpath "${1:-../gf180mcuD}")"
TECH="${PDK_DIR}/libs.tech/klayout/tech"
RUN_DIR="${PWD}/run"
mkdir -p "${RUN_DIR}"

# ---- Precheck ----
eval "$(python3 scripts/read_info.py --info info.yaml --src src --lvs LVS | sed -e 's/=\(.*\)/="\1"/')"
python3 scripts/pre_check.py --top "${top_cell}" "src/${layout}"

# ---- DRC ----
klayout -b -r "${TECH}/drc/gf180mcu.drc" \
  -rd input="src/${layout}" \
  -rd topcell="${top_cell}" \
  -rd report="${RUN_DIR}/${report}" \
  -rd variant=gf180mcuD \
  -rd decks="all,-density,inv_dut" \
  -rd run_mode=deep \
  -rd threads=max | tee "${RUN_DIR}/drc.log"
if grep -q "<visited>false</visited>" "${RUN_DIR}/${report}"; then
  echo "DRC VIOLATIONS FOUND -> FAIL (${RUN_DIR}/${report})"
  exit 1
fi

# ---- LVS ----
NETLIST_FLAG=""
if [ -n "${lvs_flag}" ]; then
  NETLIST_FLAG="-rd net_only=true"
fi
klayout -b -r "${TECH}/lvs/gf180mcu.lvs" \
  -rd input="src/${layout}" \
  -rd topcell="${top_cell}" \
  -rd schematic="${circuit}" \
  -rd report="${RUN_DIR}/${lvs_report}" \
  -rd target_netlist="${RUN_DIR}/${extracted}" \
  -rd metal_top=11K \
  -rd metal_level=5LM \
  -rd mim_option=B \
  -rd run_mode=deep \
  -rd combine=true \
  ${NETLIST_FLAG} 2>&1 | tee "${RUN_DIR}/lvs.log"
if [ -z "${NETLIST_FLAG}" ] && ! grep -q "Congratulations! Netlists match." "${RUN_DIR}/lvs.log"; then
  echo "LVS FAILED -> Netlists don't match"
  exit 1
fi

echo "ALL CHECKS PASSED: ${top_cell}"
