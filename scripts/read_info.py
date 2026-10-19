#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# RISC-V Day MPW (based on OpenSUSI TR-1um MPW template)
# LICENSE: Apache License Version 2.0, January 2004
# http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ -----

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import click
import yaml

DUT_NAME_RE = re.compile(r"^inv_dut_(\d{3})$")


def fail(message: str) -> None:
    raise click.ClickException(message)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        fail(f"info.yaml not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail(f"Invalid YAML structure in: {path}")

    return data


def require_section(data: dict[str, Any], section_name: str) -> dict[str, Any]:
    section = data.get(section_name)
    if not isinstance(section, dict):
        fail(f"Missing or invalid section: '{section_name}'")
    return section


def require_value(section: dict[str, Any], key: str, section_name: str) -> Any:
    if key not in section:
        fail(f"Missing key '{key}' in section '{section_name}'")
    value = section[key]
    if value is None or (isinstance(value, str) and not value.strip()):
        fail(f"Empty key '{key}' in section '{section_name}'")
    return value


def find_top_cell(src_dir: Path, gds_ext: str) -> str:
    """The DUT name (= top cell) is taken from the single inv_dut_NNN layout in src/."""
    layouts = sorted(src_dir.glob(f"*.{gds_ext}"))
    if len(layouts) != 1:
        names = ", ".join(p.name for p in layouts) or "none"
        fail(f"Exactly one layout file '{src_dir}/inv_dut_NNN.{gds_ext}' is required (found: {names})")

    top_cell = layouts[0].stem
    if not DUT_NAME_RE.match(top_cell):
        fail(f"Layout file name '{layouts[0].name}' must be 'inv_dut_NNN.{gds_ext}' (NNN = 3-digit DUT number)")
    return top_cell


def build_outputs(data: dict[str, Any], src_dir: Path, lvs_dir: Path) -> dict[str, str]:
    gds = require_section(data, "gds")
    lvs = require_section(data, "lvs")
    pdk = require_section(data, "pdk")

    gds_ext = str(require_value(gds, "extension", "gds")).strip()
    lvs_ext = str(require_value(lvs, "extension", "lvs")).strip()
    lvs_flag = "true" if str(require_value(lvs, "netlist_only", "lvs")).strip().lower() == "true" else ""
    pdk_repo = str(require_value(pdk, "repo", "pdk")).strip()
    pdk_ref = str(require_value(pdk, "ref", "pdk")).strip()
    pdk_dir = str(require_value(pdk, "dir", "pdk")).strip()

    top_cell = find_top_cell(src_dir, gds_ext)
    circuit = lvs_dir / f"{top_cell}.{lvs_ext}"
    if not circuit.exists():
        fail(f"Unknown DUT '{top_cell}': reference netlist '{circuit}' does not exist")

    return {
        "top_cell": top_cell,
        "layout": f"{top_cell}.{gds_ext}",
        "circuit": str(circuit),
        "report": f"{top_cell}.lyrdb",
        "lvs_report": f"{top_cell}.lvsdb",
        "extracted": f"{top_cell}.extracted",
        "lvs_flag": lvs_flag,
        "pdk_repo": pdk_repo,
        "pdk_ref": pdk_ref,
        "pdk_dir": pdk_dir,
    }


def write_github_output(outputs: dict[str, str], output_path: Path) -> None:
    with output_path.open("a", encoding="utf-8") as f:
        for key, value in outputs.items():
            f.write(f"{key}={value}\n")


@click.command()
@click.option(
    "--info",
    "info_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("info.yaml"),
    show_default=True,
    help="Path to info.yaml",
)
@click.option("--src", "src_dir", type=click.Path(path_type=Path, file_okay=False),
              default=Path("src"), show_default=True, help="Directory of the submitted layout")
@click.option("--lvs", "lvs_dir", type=click.Path(path_type=Path, file_okay=False),
              default=Path("LVS"), show_default=True, help="Directory of the reference netlists")
def main(info_path: Path, src_dir: Path, lvs_dir: Path) -> None:
    data = load_yaml(info_path)
    outputs = build_outputs(data, src_dir, lvs_dir)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        write_github_output(outputs, Path(github_output))

    for key, value in outputs.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
