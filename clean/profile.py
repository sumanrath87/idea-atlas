"""Describe the layout of every downloaded file: inner files of each zip,
column names, row counts, and a few sample rows. Writes clean/reports/profile.md.
Runs on GitHub after the raw files are pulled from the latest release."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "fetch" / "raw"
OUT = ROOT / "clean" / "reports"
SAMPLE_ROWS = 3


def describe_table(df: pd.DataFrame, label: str, lines: list[str]) -> None:
    lines.append(f"### {label}")
    lines.append(f"Rows: {len(df):,}. Columns: {len(df.columns)}.")
    lines.append("")
    lines.append("Columns: " + ", ".join(f"`{c}`" for c in df.columns[:400]))
    lines.append("")
    lines.append("```")
    lines.append(df.head(SAMPLE_ROWS).to_csv(index=False)[:3000])
    lines.append("```")
    lines.append("")


def read_any(name: str, data: bytes) -> dict[str, pd.DataFrame]:
    low = name.lower()
    if low.endswith(".csv"):
        for enc in ("utf-8", "latin-1"):
            try:
                return {name: pd.read_csv(io.BytesIO(data), dtype=str, encoding=enc, low_memory=False)}
            except UnicodeDecodeError:
                continue
    if low.endswith((".xlsx", ".xls")):
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, dtype=str, header=None, nrows=25)
        return {f"{name} [sheet {k}]": v for k, v in sheets.items()}
    if low.endswith(".txt"):
        text = data.decode("latin-1")
        return {name: pd.DataFrame({"line": text.splitlines()})}
    return {}


def main() -> int:
    lines = ["# File layouts", ""]
    for path in sorted(RAW.iterdir()):
        if "saipe__sd24-" in path.name and not path.name.endswith(("-nj.txt", "-ak.txt")):
            continue  # one state shows the layout; the rest are identical
        lines.append(f"## {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
        lines.append("")
        try:
            if path.suffix.lower() == ".zip":
                with zipfile.ZipFile(path) as z:
                    members = [m for m in z.namelist() if not m.endswith("/")]
                    lines.append("Inside: " + ", ".join(f"`{m}` ({z.getinfo(m).file_size / 1e6:.1f} MB)" for m in members[:80]))
                    lines.append("")
                    for m in members:
                        if m.lower().endswith((".csv", ".txt", ".xlsx")) and z.getinfo(m).file_size < 900e6:
                            if path.name.startswith("crdc__") and not any(
                                k in m.lower() for k in ("lea characteristics", "suspension", "expulsion",
                                                         "restraint", "referral", "enrollment", "school characteristics")):
                                continue
                            for label, df in read_any(m, z.read(m)).items():
                                describe_table(df, label, lines)
                    for m in members:
                        if m.lower().endswith((".dbf", ".shp", ".gpkg")):
                            lines.append(f"(map layer `{m}` noted, not read here)")
            else:
                for label, df in read_any(path.name, path.read_bytes()).items():
                    describe_table(df, label, lines)
        except Exception as e:  # noqa: BLE001
            lines.append(f"Could not read: {e}")
        lines.append("")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "profile.md").write_text("\n".join(lines))
    print(f"wrote {OUT / 'profile.md'} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
