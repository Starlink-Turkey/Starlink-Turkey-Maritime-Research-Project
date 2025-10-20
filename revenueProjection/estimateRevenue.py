#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
import math

# Get the repo root (parent of the script's directory)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

INPUT_DEMAND = REPO_ROOT / "starlinkAdoption" / "demandEstimate.csv"
OUT_CSV = SCRIPT_DIR / "revenueCapacity.csv"
OUT_TXT = SCRIPT_DIR / "revenueCapacity.txt"

TYPES = [
    "Container","Bulk_Carrier","Tanker_Total","RoRo_Vehicle",
    "Passenger_Cruise","General_Cargo","Livestock","Reefer",
]

# Plan priority caps (TB/month)
PLAN_CAP_TB = {"GP_50":0.05,"GP_500":0.50,"GP_1TB":1.00,"GP_2TB":2.00,"IMO_UNL": float('inf')}
# Plan monthly fees (USD)
PLAN_FEE    = {"GP_50":250,"GP_500":650,"GP_1TB":1150,"GP_2TB":2150,"IMO_UNL":2500}
# Plan mapping by vessel type
PLAN_MAP    = {
    "Container":"IMO_UNL","Tanker_Total":"IMO_UNL","Bulk_Carrier":"GP_1TB",
    "General_Cargo":"GP_500","RoRo_Vehicle":"GP_1TB","Reefer":"GP_500",
    "Livestock":"GP_500","Passenger_Cruise":"GP_2TB"
}
# Average monthly demand per ship (TB)
USAGE_TB    = {
    "Container":1.5,"Tanker_Total":1.0,"Bulk_Carrier":0.3,"General_Cargo":0.08,
    "RoRo_Vehicle":0.3,"Reefer":0.3,"Livestock":0.15,"Passenger_Cruise":15.0
}
# Optional availability multiplier per type
AVAIL = {t:1.0 for t in TYPES}

def read_row(path: Path):
    if not path.exists():
        raise SystemExit(f"[ERROR] demand file not found: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise SystemExit("[ERROR] demand file is empty")
    return df.iloc[0].to_dict()

def subs_per_ship(vtype: str):
    plan = PLAN_MAP[vtype]
    cap  = PLAN_CAP_TB[plan]
    use  = USAGE_TB[vtype]
    if cap == float('inf'):
        return 1
    return int(math.ceil(use / cap))

def main():
    row = read_row(INPUT_DEMAND)
    records, total_low, total_high = [], 0.0, 0.0

    for t in TYPES:
        lo = float(row.get(f"{t}_LEO_Unique_Low", 0))
        hi = float(row.get(f"{t}_LEO_Unique_High", 0))
        plan = PLAN_MAP[t]
        fee = PLAN_FEE[plan]
        subs = subs_per_ship(t)
        avail = AVAIL.get(t,1.0)
        usage_tb = USAGE_TB[t]

        mrr_low  = lo * subs * fee * avail
        mrr_high = hi * subs * fee * avail

        records.append({
            "Type":t,
            "Ships_Low":int(round(lo)),"Ships_High":int(round(hi)),
            "Plan":plan,
            "Cap_TB":"unlimited" if PLAN_CAP_TB[plan]==float('inf') else PLAN_CAP_TB[plan],
            "Usage_TB_per_ship": usage_tb,
            "Subs_per_ship":subs,"Fee_USD":fee,
            "MRR_Low_USD":round(mrr_low,2),"MRR_High_USD":round(mrr_high,2),
        })
        total_low += mrr_low; total_high += mrr_high

    # CSV
    pd.DataFrame.from_records(records).to_csv(OUT_CSV, index=False)

    # TXT (column-aligned, now includes Usage/ship TB)
    headers = ["Type","Ships (L–H)","Plan","Cap (TB)","Usage/ship (TB)","Subs/ship","Fee/mo","MRR Low","MRR High"]
    rows = []
    for r in records:
        rows.append([
            r["Type"],
            f'{r["Ships_Low"]:,}–{r["Ships_High"]:,}',
            r["Plan"],
            str(r["Cap_TB"]),
            f'{r["Usage_TB_per_ship"]:.2f}',
            f'{r["Subs_per_ship"]:,}',
            f'${r["Fee_USD"]:,}',
            f'${r["MRR_Low_USD"]:,.0f}',
            f'${r["MRR_High_USD"]:,.0f}',
        ])
    widths = [max(len(headers[i]), max(len(str(row[i])) for row in rows)) for i in range(len(headers))]
    def fmt(vals): return '  ' + ' | '.join(str(vals[i]).rjust(widths[i]) for i in range(len(vals)))
    lines = []
    lines.append("Revenue Estimate (Capacity-driven)")
    lines.append("Source: demandEstimate.csv (LEO-unique ships)")
    lines.append("")
    lines.append(fmt(headers))
    lines.append('  ' + '-+-'.join('-'*w for w in widths))
    for r in rows: lines.append(fmt(r))
    lines.append("")
    lines.append(f"TOTAL MRR: ${total_low:,.0f} – ${total_high:,.0f}")
    OUT_TXT.write_text('\n'.join(lines), encoding='utf-8')

if __name__ == '__main__':
    main()
