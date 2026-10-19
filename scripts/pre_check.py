#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# RISC-V Day MPW (based on OpenSUSI TR-1um MPW template)
# LICENSE: Apache License Version 2.0, January 2004
# http://www.apache.org/licenses/
# Original:
#   Copyright (c) 2025 Leo Moser <leo.moser@pm.me>
# Modified by:
#   OpenSUSI jun1okamura <jun1okamura@gmail.com>
# ----- ------ ----- ----- ------ ----- ----- ------ -----
#
# Frame checks (PR_BNDRY, shapes outside PR_BNDRY, VDD/VSS/A/Q pins)
# are done by the "inv_dut" deck of the gf180mcuD DRC.

from __future__ import annotations

import sys
from pathlib import Path

import click
import pya

EXPECTED_DBU = 0.001
EPS          = 1e-6


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"OK: {message}")
    sys.exit(0)


def same_float(a: float, b: float, eps: float = EPS) -> bool:
    return abs(a - b) <= eps


def get_single_top_cell(layout: pya.Layout, layout_file: str) -> pya.Cell:
    top_cells = list(layout.top_cells())

    if len(top_cells) == 0:
        fail(f"No top-level cell found in '{layout_file}'.")

    if len(top_cells) > 1:
        names = ", ".join(cell.name for cell in top_cells)
        fail(f"More than one top-level cell found in '{layout_file}': {names}")

    return top_cells[0]


def validate_top_name(top_cell: pya.Cell, expected_top_name: str) -> None:
    if top_cell.name != expected_top_name:
        fail(
            f"Top-level cell name '{top_cell.name}' does not match expected name "
            f"'{expected_top_name}' (must be the same as the GDS file name)."
        )


def validate_dbu(layout: pya.Layout) -> None:
    if not same_float(layout.dbu, EXPECTED_DBU):
        fail(
            f"Database unit (dbu) is {layout.dbu:.12g}, "
            f"but expected {EXPECTED_DBU:.12g}."
        )


@click.command()
@click.argument(
    "layout_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
@click.option("--top", "expected_top_name", required=True, help="Expected top cell name")
def main(layout_file: Path, expected_top_name: str) -> None:
    layout = pya.Layout()
    layout.read(str(layout_file))

    top_cell = get_single_top_cell(layout, str(layout_file))

    validate_top_name(top_cell, expected_top_name)
    print(f"OK: Top-level cell name '{expected_top_name}' matches.")

    validate_dbu(layout)
    print(f"OK: Database unit (dbu) is {layout.dbu:.3f} um.")

    ok(f"Design '{top_cell.name}' passed pre-check.")


if __name__ == "__main__":
    main()
