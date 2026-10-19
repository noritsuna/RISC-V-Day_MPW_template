# RISC-V Day MPW Template (Inverter DUT)

[![check](../../actions/workflows/check.yml/badge.svg?branch=main)](../../actions/workflows/check.yml)

gf180mcuD PDK ([ishi-kai/gf180mcuD](https://github.com/ishi-kai/gf180mcuD)) で作成したインバータ回路 (DUT) の
GDS を GitHub Actions で自動チェック (Pre-check / DRC / LVS) するテンプレートです。

[OpenSUSI/TR-1um_MPW_template](https://github.com/OpenSUSI/TR-1um_MPW_template) をベースにしています (MDP は削除)。

- [DUT datasheet template](docs/info.md)

---

## Quick Start

1. このリポジトリを Fork する
2. 割り当てられた DUT 番号 `NNN` を [dut_params.csv](dut_params.csv) で確認する
3. [inverter_base.gds](inverter_base.gds) をコピーし、PR_BNDRY の中にインバータをレイアウトする
4. Top セル名を `inv_dut_NNN` にして `src/inv_dut_NNN.gds` として保存する
   (サンプルの `src/inv_dut_000.gds` は削除してください)
5. Push する

→ CI が自動で **Pre-check / DRC / LVS** を実行します。

---

## Source Files

`src/` には GDS ファイルを **1 つだけ** 置いてください。

- `src/inv_dut_NNN.gds` : レイアウト (Top セル名も `inv_dut_NNN`)

DUT 名 (= Top セル名) はファイル名から決まります。`info.yaml` に Top セル名の設定はありません。

LVS の参照ネットリストは全 DUT 分が [LVS/](LVS/) に用意されています (`LVS/inv_dut_NNN.cdl`)。
ユーザーがネットリストを用意する必要はありません。

---

## Layout Frame (inverter_base.gds)

| 項目 | 内容 |
|------|------|
| PR_BNDRY (0/0) | 中心 (0, 0)、横 20 µm × 縦 50 µm (`-10,-25` – `10,25`) |
| VDD | Metal1 (34/0) `y = 23 … 25`、ラベル `VDD` (34/10) |
| VSS | Metal1 (34/0) `y = -25 … -23`、ラベル `VSS` (34/10) |
| A (入力) | Metal1 (34/0) `x = -10 … -9, y = -20 … 20`、ラベル `A` (34/10) |
| Q (出力) | Metal1 (34/0) `x = 9 … 10, y = -20 … 20`、ラベル `Q` (34/10) |

ルール:

- PR_BNDRY を変更しないこと
- PR_BNDRY の外側には何も (ラベルも) 置かないこと
- VDD / VSS / A / Q の Metal1 を削除・削減しないこと (Metal1 を追加して接続するのは OK)
- VDD / VSS / A / Q のラベル (34/10) を削除・移動・名前変更しないこと、34/10 にラベルを追加しないこと

インバータは `VDD`, `VSS`, `A`, `Q` を端子とし、以下の回路と一致する必要があります
(W/L は `dut_params.csv` の値)。

```
.SUBCKT inv_dut_NNN VDD VSS A Q
MP0 Q A VDD VDD <P_MODEL> W=<P_W> L=<P_L>
MN0 Q A VSS VSS <N_MODEL> W=<N_W> L=<N_L>
.ENDS
```

LVS は並列デバイスをまとめて (`combine=true`) 比較するので、マルチフィンガーで作っても
合計 W が一致すれば OK です。

---

## Configuration (info.yaml)

- `gds.extension` : レイアウトファイルの拡張子 (`gds`)
- `lvs.extension` : 参照ネットリストの拡張子 (`cdl`)
- `lvs.netlist_only` : `true` にすると抽出のみ (比較しない)
- `pdk.repo` / `pdk.ref` / `pdk.dir` : PDK リポジトリ / ブランチ・タグ / ルールデッキのディレクトリ

---

## CI Workflow

`.github/workflows/check.yml`

### Pre-check

- `src/` にある GDS が 1 つだけで、ファイル名が `inv_dut_NNN.gds` であること
- `LVS/inv_dut_NNN.cdl` が存在すること (DUT 番号が有効であること)
- Top セルが 1 つだけで、名前が `inv_dut_NNN` であること
- Database unit (dbu) が `0.001 µm` であること

### DRC

gf180mcuD の KLayout DRC (`libs.tech/klayout/tech/drc/gf180mcu.drc`) を
`-rd decks=all,-density,inv_dut` で実行します。

- 密度ルール (`density` デッキ) は実行しません
- `inv_dut` デッキでフレームをチェックします

| Rule | 内容 |
|------|------|
| `INV.PRB.1` | PR_BNDRY が inverter_base.gds と異なる |
| `INV.BND.1` | PR_BNDRY の外側に図形・ラベルがある |
| `INV.M1.1`  | VDD/VSS/A/Q の Metal1 が削除・変更されている |
| `INV.LBL.1` | VDD/VSS/A/Q ラベルが削除・移動・名前変更されている |
| `INV.LBL.2` | Metal1 ラベル (34/10) が追加されている |

レポート (`DRC_report` artifact の `.lyrdb`) は KLayout の Marker Browser で確認できます。

### LVS

gf180mcuD の KLayout LVS (`libs.tech/klayout/tech/lvs/gf180mcu.lvs`) で
`src/inv_dut_NNN.gds` と `LVS/inv_dut_NNN.cdl` を比較します
(`metal_top=11K`, `metal_level=5LM`, `mim_option=B`)。
抽出ネットリストと `.lvsdb` は `LVS_results` artifact に保存されます。

---

## Local Run

KLayout (0.30.9 以降) と `pyyaml`, `click` が必要です。

```bash
# gf180mcuD を clone (CI と同じ PDK)
git clone https://github.com/ishi-kai/gf180mcuD.git ../gf180mcuD

# CI と同じ Pre-check / DRC / LVS を実行 (結果は run/)
scripts/run_local.sh ../gf180mcuD
```

---

## Maintainer Tools

| Script | 内容 |
|--------|------|
| `scripts/gen_lvs_netlists.py` | `dut_params.csv` から `LVS/inv_dut_NNN.cdl` を全 DUT 分生成 |
| `scripts/gen_sample_dut.py`   | PDK の PCell (gdsfactory が必要) でサンプル DUT を生成 (`--dut 000`) |

```bash
python3 scripts/gen_lvs_netlists.py
python3 scripts/gen_sample_dut.py --dut 000 --pdk ../gf180mcuD
```
