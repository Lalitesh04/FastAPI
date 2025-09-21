import os
import json
import time
import threading
import subprocess
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# ---------------- CONFIG ----------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))  # current folder
SCRAPER_SCRIPT = os.path.join(BASE_PATH, "Main.py")
DATA_PATH = os.path.join(BASE_PATH, "data.json")
MOVIE_SUMMARY_PATH = os.path.join(BASE_PATH, "movie_summary.json")

TEMP_FILES = [
    os.path.join(BASE_PATH, "movie_summary.json"),
    os.path.join(BASE_PATH, "fetchedvenues.json"),
    os.path.join(BASE_PATH, "processed_venues.json")
]

SCRAPER_INTERVAL = 20 * 60  # 1 minute


# ---------------- FUNCTIONS ----------------
def clean_temp_files():
    """Remove temp files before each scrape."""
    for file in TEMP_FILES:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑 Removed: {file}")


def run_scraper_periodically():
    """Run scraper periodically, saving output to data.json."""
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

        print(f"⏱ Waiting {SCRAPER_INTERVAL/60} minutes before next run...")
        time.sleep(SCRAPER_INTERVAL)


# ---------------- LIFESPAN ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start scraper in background thread
    scraper_thread = threading.Thread(target=run_scraper_periodically, daemon=True)
    scraper_thread.start()
    print("✅ Background scraper thread started")

    yield  # App runs here

    # Cleanup logic (if needed later)
    print("🛑 App shutting down...")


# ---------------- APP ----------------
app = FastAPI(
    title="Movie Scraper API",
    version="1.0.0",
    lifespan=lifespan
)


# ---------------- ROUTES ----------------
@app.get("/movie-summary")
def get_movie_summary():
    """Serve latest data.json with last updated timestamp."""
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        last_modified = os.path.getmtime(DATA_PATH)
        last_updated = datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S")

        return JSONResponse(content={
            "last_updated": last_updated,
            "data": data
        })
    else:
        raise HTTPException(status_code=404, detail="data.json not found")
