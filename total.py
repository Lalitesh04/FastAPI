import ijson
import pandas as pd
from tabulate import tabulate

file_path = "all_shows.json"
filtered_rows = []

# Function to format numbers in Indian style (Cr, Lakh, Thousand)
def format_indian_number(num):
    num = float(num)
    if num >= 1e7:  # Crores
        return f"{num/1e7:.2f} Cr"
    elif num >= 1e5:  # Lakhs
        return f"{num/1e5:.2f} L"
    elif num >= 1e3:  # Thousands
        return f"{num/1e3:.2f} K"
    else:
        return f"{num:.2f}"

# Stream parse JSON
with open(file_path, "r", encoding="utf-8") as f:
    for item in ijson.items(f, "item"):
        item["fastfilling"] = 1 if 50 <= item["occupancy"] < 98 else 0
        item["housefull"] = 1 if item["occupancy"] >= 98 else 0
        filtered_rows.append(item)

df_filtered = pd.DataFrame(filtered_rows)

# Ensure numeric columns are correct
numeric_cols = ["total", "sold", "gross", "occupancy", "fastfilling", "housefull"]
for col in numeric_cols:
    df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce").fillna(0)

# ======================
# Helper function
# ======================
def make_summary(df, group_col):
    summary = df.groupby(group_col).agg(
        totalShows=("venue", "count"),
        totalGross=("gross", "sum"),
        totalSold=("sold", "sum"),
        totalSeats=("total", "sum"),
        fastfilling=("fastfilling", "sum"),
        housefull=("housefull", "sum"),
        avgOccupancy=("occupancy", "mean")
    ).reset_index()

    # Grand total row
    grand_total = pd.DataFrame({
        group_col: ["Grand Total"],
        "totalShows": [summary["totalShows"].sum()],
        "totalGross": [summary["totalGross"].sum()],
        "totalSold": [summary["totalSold"].sum()],
        "totalSeats": [summary["totalSeats"].sum()],
        "fastfilling": [summary["fastfilling"].sum()],
        "housefull": [summary["housefull"].sum()],
        "avgOccupancy": [
            summary["totalSold"].sum() / summary["totalSeats"].sum() * 100 
            if summary["totalSeats"].sum() > 0 else 0
        ]
    })

    summary = pd.concat([summary, grand_total], ignore_index=True)

    # Round avgOccupancy
    summary["avgOccupancy"] = summary["avgOccupancy"].round(2).astype(str) + "%"

    # Save numeric gross for sorting
    summary["_grossNum"] = summary["totalGross"]

    # Format numbers
    summary["totalGross"] = summary["_grossNum"].apply(format_indian_number)
    summary["totalSold"] = summary["totalSold"].apply(lambda x: f"{x:,.0f}")
    summary["totalSeats"] = summary["totalSeats"].apply(lambda x: f"{x:,.0f}")

    # Sort by numeric gross (keeping grand total at bottom)
    body = summary.iloc[:-1].sort_values(by="_grossNum", ascending=False)
    summary = pd.concat([body, summary.iloc[[-1]]], ignore_index=True)

    # Drop helper col
    summary = summary.drop(columns=["_grossNum"])

    return summary

# ======================
# Generate summaries
# ======================
city_summary = make_summary(df_filtered, "city")
state_summary = make_summary(df_filtered, "state")
language_summary = make_summary(df_filtered, "language")

# ======================
# Print all tables
# ======================
print("=== City-wise Summary ===")
print(tabulate(city_summary, headers="keys", tablefmt="pretty", showindex=False))

print("\n=== State-wise Summary ===")
print(tabulate(state_summary, headers="keys", tablefmt="pretty", showindex=False))

print("\n=== Language-wise Summary ===")
print(tabulate(language_summary, headers="keys", tablefmt="pretty", showindex=False))
