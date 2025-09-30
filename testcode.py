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

# City-wise aggregation (group by city only)
city_summary = df_filtered.groupby("city").agg(
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
    "city": ["Grand Total"],
    "totalShows": [city_summary["totalShows"].sum()],
    "totalGross": [city_summary["totalGross"].sum()],
    "totalSold": [city_summary["totalSold"].sum()],
    "totalSeats": [city_summary["totalSeats"].sum()],
    "fastfilling": [city_summary["fastfilling"].sum()],
    "housefull": [city_summary["housefull"].sum()],
    "avgOccupancy": [city_summary["totalSold"].sum() / city_summary["totalSeats"].sum() * 100 if city_summary["totalSeats"].sum() > 0 else 0]
})

city_summary = pd.concat([city_summary, grand_total], ignore_index=True)

# Format avgOccupancy as percentage
city_summary["avgOccupancy"] = city_summary["avgOccupancy"].round(2).astype(str) + "%"

# Export CSV
city_summary.to_csv("city_summary.csv", index=False)

# Print preview
print(tabulate(city_summary, headers="keys", tablefmt="pretty", showindex=False))
