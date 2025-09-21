import os
import json
import time
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# ---------------- CONFIG ----------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_PATH, "data.json")
SCRAPER_INTERVAL = 60 * 60  # 1 hour


# ---------------- FUNCTIONS ----------------
def clean_temp_files():
    """Remove temp files before each scrape."""
    temp_files = ["temp.json", "output.json"]
    for file in temp_files:
        file_path = os.path.join(BASE_PATH, file)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑 Removed: {file}")


def run_scraper():
    """Run scraper script once and save data.json."""
    try:
        # Example: Replace with your actual scraper call
        os.system(f"python3 {os.path.join(BASE_PATH, 'scraper_runner.py')}")
        print("✅ Scraper run completed.")
    except Exception as e:
        print(f"❌ Scraper error: {e}")


def run_scraper_periodically():
    """Run scraper periodically in background thread."""
    while True:
        clean_temp_files()
        run_scraper()
        print(f"⏱ Waiting {SCRAPER_INTERVAL/60} minutes before next run...")
        time.sleep(SCRAPER_INTERVAL)


# ---------------- LIFESPAN ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 App starting...")

    # Start background thread for scraper
    threading.Thread(target=run_scraper_periodically, daemon=True).start()

    yield  # App runs here

    print("🛑 App shutting down...")


# ---------------- APP ----------------
app = FastAPI(
    title="Movie Scraper API",
    version="1.0.0",
    lifespan=lifespan
)

# ---------------- CORS ----------------
origins = [
    "http://localhost:3000",   # local frontend
    "https://bookmyshow-api.vercel.app"  # deployed frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # use ["*"] for all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- ROUTES ----------------
# ---------------- ROUTES ----------------
@app.get("/movie-summary")
def get_movie_summary():
    """Serve processed data.json"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return JSONResponse({
            "last_updated": datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p"),
            "data": data
        })
    else:
        raise HTTPException(status_code=404, detail="data.json not found")


@app.get("/raw-movie-summary")
def get_raw_movie_summary():
    """Serve raw movie_summary.json file"""
    raw_file = os.path.join(BASE_PATH, "movie_summary.json")

    if os.path.exists(raw_file):
        with open(raw_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return JSONResponse({
            "last_updated": datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p"),
            "data": data
        })
    else:
        raise HTTPException(status_code=404, detail="movie_summary.json not found")


