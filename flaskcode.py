import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ---------------- CONFIG ----------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_PATH, "data.json")

# ---------------- APP ----------------
app = FastAPI(
    title="Movie Scraper API",
    version="1.0.0",
)

# ---------------- CORS ----------------
origins = [
    "http://localhost:3000",  # your frontend URL
    "https://bookmyshow-api.vercel.app/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
