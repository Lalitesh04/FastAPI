import ijson
import pandas as pd
from tabulate import tabulate

file_path = "all_shows.json"
filtered_rows = []

# Stream parse JSON
with open(file_path, "r", encoding="utf-8") as f:
    for item in ijson.items(f, "item"):
        # Add fastfilling/housefull flags
        item["fastfilling"] = 1 if 50 <= item["occupancy"] < 98 else 0
        item["housefull"] = 1 if item["occupancy"] >= 98 else 0
        filtered_rows.append(item)

# Convert filtered rows to DataFrame
df_filtered = pd.DataFrame(filtered_rows)

# Ensure numeric columns are correct
numeric_cols = ["total", "sold", "gross", "occupancy", "fastfilling", "housefull"]
for col in numeric_cols:
    df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce").fillna(0)

# ----------------------
# 1. City-wise summary
# ----------------------
city_summary = df_filtered.groupby("city").agg(
    totalShows=("venue", "count"),
    totalGross=("gross", "sum"),
    totalSold=("sold", "sum"),
    totalSeats=("total", "sum"),
    fastfilling=("fastfilling", "sum"),
    housefull=("housefull", "sum"),
    avgOccupancy=("occupancy", "mean")
).reset_index()

city_grand_total = pd.DataFrame({
    "city": ["Grand Total"],
    "totalShows": [city_summary["totalShows"].sum()],
    "totalGross": [city_summary["totalGross"].sum()],
    "totalSold": [city_summary["totalSold"].sum()],
    "totalSeats": [city_summary["totalSeats"].sum()],
    "fastfilling": [city_summary["fastfilling"].sum()],
    "housefull": [city_summary["housefull"].sum()],
    "avgOccupancy": [city_summary["totalSold"].sum() / city_summary["totalSeats"].sum() * 100 if city_summary["totalSeats"].sum() > 0 else 0]
})

city_summary = pd.concat([city_summary, city_grand_total], ignore_index=True)
city_summary["avgOccupancy"] = city_summary["avgOccupancy"].round(2).astype(str) + "%"

city_summary.to_csv("city_summary.csv", index=False)

# ----------------------
# 2. State-wise summary
# ----------------------
state_summary = df_filtered.groupby("state").agg(
    totalShows=("venue", "count"),
    totalGross=("gross", "sum"),
    totalSold=("sold", "sum"),
    totalSeats=("total", "sum"),
    fastfilling=("fastfilling", "sum"),
    housefull=("housefull", "sum"),
    avgOccupancy=("occupancy", "mean")
).reset_index()

state_grand_total = pd.DataFrame({
    "state": ["Grand Total"],
    "totalShows": [state_summary["totalShows"].sum()],
    "totalGross": [state_summary["totalGross"].sum()],
    "totalSold": [state_summary["totalSold"].sum()],
    "totalSeats": [state_summary["totalSeats"].sum()],
    "fastfilling": [state_summary["fastfilling"].sum()],
    "housefull": [state_summary["housefull"].sum()],
    "avgOccupancy": [state_summary["totalSold"].sum() / state_summary["totalSeats"].sum() * 100 if state_summary["totalSeats"].sum() > 0 else 0]
})

state_summary = pd.concat([state_summary, state_grand_total], ignore_index=True)
state_summary["avgOccupancy"] = state_summary["avgOccupancy"].round(2).astype(str) + "%"

state_summary.to_csv("state_summary.csv", index=False)

# ----------------------
# 3. Language-wise summary
# ----------------------
language_summary = df_filtered.groupby("language").agg(
    totalShows=("venue", "count"),
    totalGross=("gross", "sum"),
    totalSold=("sold", "sum"),
    totalSeats=("total", "sum"),
    fastfilling=("fastfilling", "sum"),
    housefull=("housefull", "sum"),
    avgOccupancy=("occupancy", "mean")
).reset_index()

language_grand_total = pd.DataFrame({
    "language": ["Grand Total"],
    "totalShows": [language_summary["totalShows"].sum()],
    "totalGross": [language_summary["totalGross"].sum()],
    "totalSold": [language_summary["totalSold"].sum()],
    "totalSeats": [language_summary["totalSeats"].sum()],
    "fastfilling": [language_summary["fastfilling"].sum()],
    "housefull": [language_summary["housefull"].sum()],
    "avgOccupancy": [language_summary["totalSold"].sum() / language_summary["totalSeats"].sum() * 100 if language_summary["totalSeats"].sum() > 0 else 0]
})

language_summary = pd.concat([language_summary, language_grand_total], ignore_index=True)
language_summary["avgOccupancy"] = language_summary["avgOccupancy"].round(2).astype(str) + "%"

language_summary.to_csv("language_summary.csv", index=False)

# ----------------------
# Print all tables
# ----------------------
print("=== City-wise Summary ===")
print(tabulate(city_summary, headers="keys", tablefmt="pretty", showindex=False))
print("\n=== State-wise Summary ===")
print(tabulate(state_summary, headers="keys", tablefmt="pretty", showindex=False))
print("\n=== Language-wise Summary ===")
print(tabulate(language_summary, headers="keys", tablefmt="pretty", showindex=False))
