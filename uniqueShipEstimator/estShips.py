import pandas as pd
from pathlib import Path

# --- Config ---
CSV_PATH = Path("istanbul_strait_transits.csv")   # totals-only input
OUTPUT_PATH = CSV_PATH.with_name("istanbul_unique_estimates.csv")

ANCHOR_YEAR = 2021
ANCHOR_TOTAL = 38551       # total transits in anchor year
ANCHOR_UNIQUE = 6071       # unique vessels in anchor year
DELTA = 0.15               # ±15% band

# --- Load ---
df = pd.read_csv(CSV_PATH)

# --- Compute repeat factor r from anchor year ---
r = ANCHOR_TOTAL / ANCHOR_UNIQUE

# --- Compute estimates ---
out = df.copy()
out["Est_Unique"] = (out["Istanbul_Strait_Total_Transits"] / r).round(0).astype(int)
out["Est_Unique_Low"] = (out["Istanbul_Strait_Total_Transits"] / (r * (1 + DELTA))).round(0).astype(int)
out["Est_Unique_High"] = (out["Istanbul_Strait_Total_Transits"] / (r * (1 - DELTA))).round(0).astype(int)

# --- Save to a new file ---
out.to_csv(OUTPUT_PATH, index=False)
print(f"Saved estimates to: {OUTPUT_PATH.resolve()}")
print(f"Repeat factor r = {r:.6f}")
