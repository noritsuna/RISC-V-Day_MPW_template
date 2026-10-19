#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# RISC-V Day MPW
# LICENSE: Apache License Version 2.0, January 2004
# http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ -----
"""Generate LVS reference netlists (CDL) for every DUT listed in dut_params.csv."""

from __future__ import annotations

import csv
from pathlib import Path

import click

DUT_PREFIX = "inv_dut_"
PINS = ("VDD", "VSS", "A", "Q")


def read_params(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        reader.fieldnames = [name.strip() for name in reader.fieldnames or []]
        return [{k: v.strip() for k, v in row.items()} for row in reader if row.get("DUT_NUM")]


def build_cdl(row: dict[str, str]) -> str:
    name = f"{DUT_PREFIX}{row['DUT_NUM']}"
    return "\n".join(
        [
            f"* {name} : CMOS inverter",
            f"*   PMOS {row['P_MODEL']} W={row['P_W']} L={row['P_L']}",
            f"*   NMOS {row['N_MODEL']} W={row['N_W']} L={row['N_L']}",
            f".SUBCKT {name} {' '.join(PINS)}",
            "*.PININFO VDD:B VSS:B A:I Q:O",
            f"MP0 Q A VDD VDD {row['P_MODEL']} W={row['P_W']} L={row['P_L']}",
            f"MN0 Q A VSS VSS {row['N_MODEL']} W={row['N_W']} L={row['N_L']}",
            ".ENDS",
            "",
        ]
    )


@click.command()
@click.option("--csv", "csv_path", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=Path("dut_params.csv"), show_default=True, help="DUT parameter table")
@click.option("--out", "out_dir", type=click.Path(file_okay=False, path_type=Path),
              default=Path("LVS"), show_default=True, help="Output directory")
def main(csv_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_params(csv_path)
    for row in rows:
        path = out_dir / f"{DUT_PREFIX}{row['DUT_NUM']}.cdl"
        path.write_text(build_cdl(row), encoding="utf-8")
    print(f"Generated {len(rows)} netlists in {out_dir}/")


if __name__ == "__main__":
    main()
