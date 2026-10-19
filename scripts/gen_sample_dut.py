#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# RISC-V Day MPW
# LICENSE: Apache License Version 2.0, January 2004
# http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ -----
"""Generate a sample inverter DUT layout (src/inv_dut_NNN.gds) from inverter_base.gds.

The transistors are drawn with the gf180mcuD PCell generators (requires gdsfactory).
This is a reference/test layout generator for the CI flow, not a design tool.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import pya

from gen_lvs_netlists import DUT_PREFIX, read_params

M1 = (34, 0)
M1_W = 0.38  # Metal1 route width [um]
M1_SPACE = 0.25  # Metal1 route spacing [um] (M1.2a: 0.23)

# Base frame (inverter_base.gds) Metal1 pins [um]
VDD_RAIL_Y = 23.0
VSS_RAIL_Y = -23.0
A_PIN_X = -9.0
Q_PIN_X = 9.0

# Device origins [um]
NMOS_ORIGIN = (-1.0, -15.0)
PMOS_ORIGIN = (-1.0, 4.0)


def to_um(value: str) -> float:
    return float(value.strip().rstrip("u"))


def volt_of(model: str) -> str:
    return {"03v3": "3.3V", "05v0": "5V", "06v0": "6V"}[model.split("_")[1]]


def draw_device(layout: pya.Layout, pdk_macros: Path, kind: str, model: str, w: float, l: float) -> pya.Cell:
    sys.path.insert(0, str(pdk_macros))
    from cells.draw_fet import draw_nfet, draw_pfet  # noqa: E402
    from cells.pcell_utilities import gf_to_pya  # noqa: E402

    draw = draw_nfet if kind == "nfet" else draw_pfet
    comp = draw(
        l_gate=l, w_gate=w, volt=volt_of(model), bulk="Bulk Tie", nf=1,
        # gates face each other between the two devices
        gate_con_pos="top" if kind == "nfet" else "bottom",
        inter_sd_l=0.52, grw=0.38,
    )
    return gf_to_pya(layout, comp, kind)


def classify_m1(layout: pya.Layout, cell: pya.Cell, w: float) -> dict[str, pya.DBox]:
    """Return gate contact and source/drain/tap Metal1 boxes of a single-finger device."""
    li = layout.layer(*M1)
    boxes = [s.dbbox() for s in cell.shapes(li).each()]
    gate = [b for b in boxes if b.top <= 0 or b.bottom >= w]
    strips = sorted((b for b in boxes if b not in gate), key=lambda b: b.left)
    if len(gate) != 1 or len(strips) != 3:
        raise click.ClickException(f"Unexpected Metal1 structure in {cell.name}")
    return {"gate": gate[0], "source": strips[0], "drain": strips[1], "tap": strips[2]}


def moved(box: pya.DBox, origin: tuple[float, float]) -> pya.DBox:
    return box.moved(origin[0], origin[1])


@click.command()
@click.option("--dut", "dut_num", required=True, help="DUT number (e.g. 000)")
@click.option("--csv", "csv_path", type=click.Path(exists=True, path_type=Path),
              default=Path("dut_params.csv"), show_default=True)
@click.option("--base", "base_gds", type=click.Path(exists=True, path_type=Path),
              default=Path("inverter_base.gds"), show_default=True)
@click.option("--pdk", "pdk_root", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=Path("../gf180mcuD"), show_default=True,
              help="gf180mcuD PDK directory")
@click.option("--out", "out_dir", type=click.Path(file_okay=False, path_type=Path),
              default=Path("src"), show_default=True)
def main(dut_num: str, csv_path: Path, base_gds: Path, pdk_root: Path, out_dir: Path) -> None:
    rows = {r["DUT_NUM"]: r for r in read_params(csv_path)}
    if dut_num not in rows:
        raise click.ClickException(f"DUT {dut_num} not found in {csv_path}")
    row = rows[dut_num]
    name = f"{DUT_PREFIX}{dut_num}"

    layout = pya.Layout()
    layout.read(str(base_gds))
    top = layout.top_cell()
    top.name = name

    pdk_macros = pdk_root / "libs.tech" / "klayout" / "tech" / "pymacros"
    p_w, p_l = to_um(row["P_W"]), to_um(row["P_L"])
    n_w, n_l = to_um(row["N_W"]), to_um(row["N_L"])
    pcell = draw_device(layout, pdk_macros, "pfet", row["P_MODEL"], p_w, p_l)
    ncell = draw_device(layout, pdk_macros, "nfet", row["N_MODEL"], n_w, n_l)
    pm = {k: moved(b, PMOS_ORIGIN) for k, b in classify_m1(layout, pcell, p_w).items()}
    nm = {k: moved(b, NMOS_ORIGIN) for k, b in classify_m1(layout, ncell, n_w).items()}
    top.insert(pya.DCellInstArray(pcell.cell_index(), pya.DTrans(*PMOS_ORIGIN)))
    top.insert(pya.DCellInstArray(ncell.cell_index(), pya.DTrans(*NMOS_ORIGIN)))

    m1 = top.shapes(layout.layer(*M1))
    # Source and bulk tap to the supply rails
    for key in ("source", "tap"):
        m1.insert(pya.DBox(pm[key].left, pm[key].bottom, pm[key].right, VDD_RAIL_Y))
        m1.insert(pya.DBox(nm[key].left, VSS_RAIL_Y, nm[key].right, nm[key].top))
    # Gates to pin A
    for gate in (pm["gate"], nm["gate"]):
        m1.insert(pya.DBox(A_PIN_X, gate.bottom, gate.right, gate.top))
    # Drains to pin Q
    # (the drain risers keep Metal1 spacing to the gate contacts)
    y_mid = (pm["gate"].bottom + nm["gate"].top) / 2.0
    p_x = max(pm["drain"].left, pm["gate"].right + M1_SPACE)
    n_x = max(nm["drain"].left, nm["gate"].right + M1_SPACE)
    m1.insert(pya.DBox(p_x, y_mid - M1_W / 2, pm["drain"].right, pm["drain"].top))
    m1.insert(pya.DBox(n_x, nm["drain"].bottom, nm["drain"].right, y_mid + M1_W / 2))
    m1.insert(pya.DBox(min(p_x, n_x), y_mid - M1_W / 2, Q_PIN_X, y_mid + M1_W / 2))

    top.flatten(True)
    m1_li = layout.layer(*M1)
    merged = pya.Region(top.shapes(m1_li)).merged()
    top.shapes(m1_li).clear()
    top.shapes(m1_li).insert(merged)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.gds"
    layout.write(str(out_path))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
