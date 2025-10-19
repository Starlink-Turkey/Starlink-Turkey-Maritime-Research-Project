from pathlib import Path
import csv
import math

# ====================CONFIG====================

INPUT_CSV = Path("bosphorus_vessel_types_2020_2024.csv")
TARGET_YEAR = 2024

# LEO adoption rates (low, high) per vessel type:
ADOPTION = {
    "Container": (0.10, 0.20),
    "Bulk_Carrier": (0.03, 0.07),
    "Tanker_Total": (0.10, 0.20),
    "RoRo_Vehicle": (0.02, 0.05),
    "Passenger_Cruise": (0.60, 0.90),
    "General_Cargo": (0.01, 0.03),
    "Livestock": (0.00, 0.02),
    "Reefer": (0.00, 0.03),
}

# OPTIONAL manual input. If not None, the script uses these counts.
MANUAL_COUNTS = None
# MANUAL_COUNTS = {
#     "Container": 3600,
#     "Bulk_Carrier": 8800,
#     "Tanker_Total": 9700,
#     "RoRo_Vehicle": 600,
#     "Passenger_Cruise": 2800,
#     "General_Cargo": 15500,
#     "Livestock": 470,
#     "Reefer": 10,
# }

OUTPUT_CSV = Path("leoProjection.csv")
OUTPUT_TXT = Path("leoProjection.txt")
OUTPUT_SVG = Path("leoProjection.svg")


# ==================== end config ====================


def validate_counts(keys, counts):
    missing = [k for k in keys if k not in counts]
    if missing:
        raise ValueError(f"Counts missing required types: {missing}")
    for k in keys:
        if counts[k] < 0:
            raise ValueError(f"Negative count for {k}: {counts[k]}")


def read_counts_from_csv(csv_path: Path, year: int, keys):
    if not csv_path.exists():
        raise FileNotFoundError(f"INPUT_CSV not found: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        found = None
        for row in rdr:
            try:
                if int(row["Year"]) == year:
                    found = row
                    break
            except Exception:
                pass
        if not found:
            raise ValueError(f"Year {year} not found in {csv_path}")
        total = float(found["Total_Transits"])
        counts = {k: float(found[k]) for k in keys}
        return counts, total


def project_from_counts(counts, adoption):
    per_type = {}
    low_total = 0.0
    high_total = 0.0
    for k, (lo, hi) in adoption.items():
        c = float(counts[k])
        lo_est = c * lo
        hi_est = c * hi
        per_type[k] = {"count": c, "low": lo_est, "high": hi_est}
        low_total += lo_est
        high_total += hi_est
    return per_type, round(low_total), round(high_total)


def save_summary_csv(year, total, keys, per_type, low_total, high_total, out_csv: Path):
    fields = ["Year", "Total_Transits", "Est_LEO_Transits_Low", "Est_LEO_Transits_High",
              "Est_LEO_Share_Min_%", "Est_LEO_Share_Max_%"]
    for k in keys:
        fields += [f"{k}_Count", f"{k}_LEO_Low", f"{k}_LEO_High"]

    row = {
        "Year": year,
        "Total_Transits": int(total) if float(total).is_integer() else total,
        "Est_LEO_Transits_Low": int(low_total),
        "Est_LEO_Transits_High": int(high_total),
        "Est_LEO_Share_Min_%": round(100.0 * low_total / total, 1) if total > 0 else "",
        "Est_LEO_Share_Max_%": round(100.0 * high_total / total, 1) if total > 0 else "",
    }
    for k in keys:
        row[f"{k}_Count"]    = int(round(per_type[k]["count"]))
        row[f"{k}_LEO_Low"]  = int(round(per_type[k]["low"]))
        row[f"{k}_LEO_High"] = int(round(per_type[k]["high"]))

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow(row)


def save_text_report(year, total, keys, per_type, low_total, high_total, out_txt: Path):
    lines = []
    lines.append("Bosphorus LEO Adoption Projection (Single Year)\n")
    lines.append(f"Year: {year}")
    lines.append(f"Total Transits: {int(total)}")
    lo_pct = round(100 * low_total / total, 1) if total > 0 else 0
    hi_pct = round(100 * high_total / total, 1) if total > 0 else 0
    lines.append(f"Estimated LEO-Equipped Transits: {low_total} – {high_total} ({lo_pct}% – {hi_pct}%)\n")
    lines.append("By Vessel Type (count, LEO low–high, % of type using LEO):")
    for k in keys:
        c = int(round(per_type[k]["count"]))
        lo = int(round(per_type[k]["low"]))
        hi = int(round(per_type[k]["high"]))
        lo_rate, hi_rate = ADOPTION[k]
        lines.append(f"- {k}: count={c}, LEO={lo}–{hi} ({round(100*lo_rate,1)}%–{round(100*hi_rate,1)}%)")
    out_txt.write_text("\n".join(lines), encoding="utf-8")


def nice_num(n):
    # round to nice tick step
    exp = math.floor(math.log10(n)) if n > 0 else 0
    base = n / (10 ** exp) if n > 0 else 0
    if base < 1.5:
        step = 1
    elif base < 3:
        step = 2
    elif base < 7:
        step = 5
    else:
        step = 10
    return step * (10 ** exp)


def save_svg_bar_chart(year, keys, per_type, out_svg: Path, title="Estimated LEO-Equipped Transits by Vessel Type"):
    labels = list(keys)
    mid_vals = [(per_type[k]["low"] + per_type[k]["high"]) / 2.0 for k in labels]

    # SVG canvas settings
    W, H = 1000, 600
    margin = dict(left=120, right=40, top=70, bottom=140)
    plot_w = W - margin["left"] - margin["right"]
    plot_h = H - margin["top"] - margin["bottom"]

    max_val = max(mid_vals) if mid_vals else 0
    ymax = max_val * 1.15 if max_val > 0 else 1
    # y ticks: 5 steps
    y_step_raw = ymax / 5
    y_step = nice_num(y_step_raw)
    ymax = y_step * math.ceil(ymax / y_step)

    # Bar layout
    n = len(labels)
    bar_w = plot_w / (n * 1.25) if n > 0 else 0
    bar_gap = bar_w * 0.25

    def x_for(i):
        return margin["left"] + i * (bar_w + bar_gap) + bar_gap

    def y_for(v):
        return margin["top"] + plot_h - (v / ymax) * plot_h

    # Build SVG
    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    # Title
    parts.append(f'<text x="{W/2}" y="{margin["top"]/2}" text-anchor="middle" font-family="Arial" font-size="20">{title} ({year})</text>')

    # Axes
    # Y axis
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"]+plot_h}" stroke="black"/>')
    # X axis
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"]+plot_h}" x2="{margin["left"]+plot_w}" y2="{margin["top"]+plot_h}" stroke="black"/>')

    # Y ticks & labels
    tick = 0.0
    while tick <= ymax + 1e-9:
        y = y_for(tick)
        parts.append(f'<line x1="{margin["left"]-5}" y1="{y}" x2="{margin["left"]}" y2="{y}" stroke="black"/>')
        parts.append(f'<text x="{margin["left"]-10}" y="{y+4}" text-anchor="end" font-family="Arial" font-size="12">{int(tick)}</text>')
        tick += y_step

    # Bars and x labels
    for i, (lab, val) in enumerate(zip(labels, mid_vals)):
        x = x_for(i)
        y = y_for(val)
        h = (val / ymax) * plot_h if ymax > 0 else 0
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="steelblue"/>')
        # value label
        parts.append(f'<text x="{x + bar_w/2:.1f}" y="{y-6:.1f}" text-anchor="middle" font-family="Arial" font-size="12">{int(round(val))}</text>')
        # x tick label (wrap to two lines if long)
        words = lab.split("_")
        l1 = " ".join(words[:2])
        l2 = " ".join(words[2:]) if len(words) > 2 else ""
        parts.append(f'<text x="{x + bar_w/2:.1f}" y="{margin["top"]+plot_h+20}" text-anchor="middle" font-family="Arial" font-size="12">{l1}</text>')
        if l2:
            parts.append(f'<text x="{x + bar_w/2:.1f}" y="{margin["top"]+plot_h+36}" text-anchor="middle" font-family="Arial" font-size="12">{l2}</text>')

    # Y label
    parts.append(f'<text x="{margin["left"]-70}" y="{margin["top"] + plot_h/2}" text-anchor="middle" font-family="Arial" font-size="12" transform="rotate(-90 {margin["left"]-70},{margin["top"] + plot_h/2})">Estimated LEO-Equipped Transits (midpoint)</text>')

    parts.append('</svg>')

    out_svg.write_text("\n".join(parts), encoding="utf-8")


def main():
    keys = list(ADOPTION.keys())

    if MANUAL_COUNTS is not None:
        validate_counts(keys, MANUAL_COUNTS)
        counts = MANUAL_COUNTS
        total = sum(float(counts[k]) for k in keys)
        year = "manual"
    else:
        counts, total = read_counts_from_csv(INPUT_CSV, TARGET_YEAR, keys)
        year = TARGET_YEAR

    per_type, low_total, high_total = project_from_counts(counts, ADOPTION)

    # Sanity: warn if sum of type counts deviates from provided Total_Transits (if CSV mode)
    type_sum = sum(counts.values())
    if MANUAL_COUNTS is None and abs(type_sum - total) > 1e-6:
        print(f"[WARN] Sum of type counts ({type_sum:.0f}) != Total_Transits ({total:.0f}). Percentages use Total_Transits.")

    save_summary_csv(year, total, keys, per_type, low_total, high_total, OUTPUT_CSV)
    save_text_report(year, total, keys, per_type, low_total, high_total, OUTPUT_TXT)
    save_svg_bar_chart(year, keys, per_type, OUTPUT_SVG)

    print(f"Saved:\n- {OUTPUT_CSV.resolve()}\n- {OUTPUT_TXT.resolve()}\n- {OUTPUT_SVG.resolve()}")


if __name__ == "__main__":
    main()
