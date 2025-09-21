import os
import json
import time
import subprocess
from datetime import datetime

# ---------------- CONFIG ----------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
SCRAPER_SCRIPT = os.path.join(BASE_PATH, "Main.py")
DATA_PATH = os.path.join(BASE_PATH, "data.json")
MOVIE_SUMMARY_PATH = os.path.join(BASE_PATH, "movie_summary.json")
TEMP_FILES = [
    os.path.join(BASE_PATH, "movie_summary.json"),
    os.path.join(BASE_PATH, "fetchedvenues.json"),
    os.path.join(BASE_PATH, "processed_venues.json")
]

SCRAPER_INTERVAL = 60 * 60  # 1 hour

# ---------------- FUNCTIONS ----------------
def clean_temp_files():
    for file in TEMP_FILES:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑 Removed: {file}")

def run_scraper():
    while True:
        print(f"🚀 Running scraper at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        clean_temp_files()
        try:
            subprocess.run(["python", SCRAPER_SCRIPT], check=True)
            if os.path.exists(MOVIE_SUMMARY_PATH):
                with open(MOVIE_SUMMARY_PATH, "r", encoding="utf-8") as f:
                    movie_summary = json.load(f)
                with open(DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump(movie_summary, f, indent=2, ensure_ascii=False)
                print(f"✅ Movie summary saved to {DATA_PATH}")
        except Exception as e:
            print(f"⚠️ Scraper failed: {e}")
        print(f"⏱ Waiting {SCRAPER_INTERVAL / 60} minutes before next run...")
        time.sleep(SCRAPER_INTERVAL)

# ---------------- ENTRY ----------------
if __name__ == "__main__":
    run_scraper()
