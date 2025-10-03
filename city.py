import ijson
import pandas as pd
from tabulate import tabulate

file_path = "all_shows.json"
filtered_rows = []

# ======================
# Helper: Format numbers in Indian style
# ======================
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


# ======================
# Load JSON
# ======================
with open(file_path, "r", encoding="utf-8") as f:
    for item in ijson.items(f, "item"):
        item["fastfilling"] = 1 if 50 <= item["occupancy"] < 98 else 0
        item["housefull"] = 1 if item["occupancy"] >= 98 else 0
        filtered_rows.append(item)

df_filtered = pd.DataFrame(filtered_rows)

# Ensure numeric columns
numeric_cols = ["total", "sold", "gross", "occupancy", "fastfilling", "housefull"]
for col in numeric_cols:
    df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce").fillna(0)


# ======================
# City-wise summary grouped by state
# ======================
def make_city_summary(df):
    summary = df.groupby(["state", "city"]).agg(
        totalShows=("venue", "count"),
        totalGross=("gross", "sum"),
        totalSold=("sold", "sum"),
        totalSeats=("total", "sum"),
        fastfilling=("fastfilling", "sum"),
        housefull=("housefull", "sum"),
        avgOccupancy=("occupancy", "mean")
    ).reset_index()

    # Grand Total
    grand_total = pd.DataFrame({
        "state": ["Grand Total"],
        "city": [""],
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

    # Helper for sorting
    summary["_grossNum"] = summary["totalGross"]

    # Format numbers
    summary["totalGross"] = summary["_grossNum"].apply(format_indian_number)
    summary["totalSold"] = summary["totalSold"].apply(lambda x: f"{x:,.0f}")
    summary["totalSeats"] = summary["totalSeats"].apply(lambda x: f"{x:,.0f}")

    # Sort by state + gross
    body = summary.iloc[:-1].sort_values(
        by=["state", "_grossNum"], ascending=[True, False]
    )
    summary = pd.concat([body, summary.iloc[[-1]]], ignore_index=True)

    return summary.drop(columns=["_grossNum"])


# ======================
# Language + Dimension summary
# ======================
def make_lang_dim_summary(df):
    summary = df.groupby(["language", "dimension"]).agg(
        totalShows=("venue", "count"),
        totalGross=("gross", "sum"),
        totalSold=("sold", "sum"),
        totalSeats=("total", "sum"),
        fastfilling=("fastfilling", "sum"),
        housefull=("housefull", "sum"),
        avgOccupancy=("occupancy", "mean")
    ).reset_index()

    # Grand Total
    grand_total = pd.DataFrame({
        "language": ["Grand Total"],
        "dimension": [""],
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

    # Helper for sorting
    summary["_grossNum"] = summary["totalGross"]

    # Format numbers
    summary["totalGross"] = summary["_grossNum"].apply(format_indian_number)
    summary["totalSold"] = summary["totalSold"].apply(lambda x: f"{x:,.0f}")
    summary["totalSeats"] = summary["totalSeats"].apply(lambda x: f"{x:,.0f}")

    # Sort by language + gross
    body = summary.iloc[:-1].sort_values(
        by=["language", "_grossNum"], ascending=[True, False]
    )
    summary = pd.concat([body, summary.iloc[[-1]]], ignore_index=True)

    return summary.drop(columns=["_grossNum"])


# ======================
# Top 20 Most Grossed Cities
# ======================
def make_top_cities(df, top_n=20):
    summary = df.groupby(["state", "city"]).agg(
        totalShows=("venue", "count"),
        totalGross=("gross", "sum"),
        totalSold=("sold", "sum"),
        totalSeats=("total", "sum"),
        fastfilling=("fastfilling", "sum"),
        housefull=("housefull", "sum"),
        avgOccupancy=("occupancy", "mean")
    ).reset_index()

    # Sort by gross and take top N
    summary = summary.sort_values(by="totalGross", ascending=False).head(top_n)

    # Round avgOccupancy
    summary["avgOccupancy"] = summary["avgOccupancy"].round(2).astype(str) + "%"

    # Helper
    summary["_grossNum"] = summary["totalGross"]

    # Format numbers
    summary["totalGross"] = summary["_grossNum"].apply(format_indian_number)
    summary["totalSold"] = summary["totalSold"].apply(lambda x: f"{x:,.0f}")
    summary["totalSeats"] = summary["totalSeats"].apply(lambda x: f"{x:,.0f}")

    return summary.drop(columns=["_grossNum"])


# ======================
# Generate & Print Summaries
# ======================
city_summary = make_city_summary(df_filtered)
lang_dim_summary = make_lang_dim_summary(df_filtered)
top_cities_summary = make_top_cities(df_filtered, top_n=20)

print("=== City-wise Summary (Grouped by State, Cities by Gross Desc) ===")
print(tabulate(city_summary, headers="keys", tablefmt="pretty", showindex=False))

print("\n=== Language + Dimension Summary ===")
print(tabulate(lang_dim_summary, headers="keys", tablefmt="pretty", showindex=False))

print("\n=== Top 20 Cities by Gross ===")
print(tabulate(top_cities_summary, headers="keys", tablefmt="pretty", showindex=False))
