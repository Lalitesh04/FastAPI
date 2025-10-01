import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import cloudscraper
import random
import pandas as pd
from collections import defaultdict

# ---------------- CONFIG ----------------
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="Enter the date in YYYY-MM-DD format")
args = parser.parse_args()

print(f"Fetching box office data for: {args.date}")

NUM_WORKERS = 5
MAX_ERRORS = 10

IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)

scraper = cloudscraper.create_scraper()
lock = threading.Lock()
error_count = 0

# Example User-Agent pool
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.1 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.1 (Windows NT 11.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}",
    # Chrome on Mac
    "Mozilla/5.1 (Macintosh; Intel Mac OS X 10_{minor}_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.38",
    # Safari on Mac
    "Mozilla/5.1 (Macintosh; Intel Mac OS X 10_{minor}_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Safari/605.1.16",
]


def get_random_user_agent():
    template = random.choice(USER_AGENTS)
    return template.format(
        version=f"{random.randint(70,120)}.0.{random.randint(1000,5000)}.{random.randint(0,150)}",
        minor=random.randint(12, 15),
        safari_ver=f"{random.randint(13,17)}.0.{random.randint(1,3)}",
    )


def get_random_ip():
    return ".".join(str(random.randint(1, 255)) for _ in range(4))


def get_headers():
    random_ip = get_random_ip()
    return {
        "User-Agent": get_random_user_agent(),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://in.bookmyshow.com",
        "Referer": "https://in.bookmyshow.com/",
        "X-Forwarded-For": random_ip,
        "Client-IP": random_ip,
    }


headers = get_headers()

# ---------------- VENUES LOADER ----------------
def load_all_venues(path="venues.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_rgross(value):
    if value >= 1e7:
        return f"{round(value/1e7, 2)} Cr"
    elif value >= 1e5:
        return f"{round(value/1e5, 2)} L"
    elif value >= 1e3:
        return f"{round(value/1e3, 2)} K"
    else:
        return str(round(value, 2))

ALL_VENUES = load_all_venues()
# ---------------- FETCH DATA ----------------
ALL_SHOWS = []

# Load saved ALL_SHOWS if present  # NEW
if os.path.exists("all_shows.json"):
    with open("all_shows.json", "r", encoding="utf-8") as f:
        try:
            ALL_SHOWS = json.load(f)
            print(f"📂 Loaded {len(ALL_SHOWS)} saved shows from all_shows.json")
        except:
            ALL_SHOWS = []


# ---------------- FETCH DATA ----------------
def fetch_data(venue_code):
    url = f"https://in.bookmyshow.com/api/v2/mobile/showtimes/byvenue?venueCode={venue_code}&dateCode={DATE_CODE}"
    try:
        res = scraper.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"⚠️ Failed {venue_code}: {e}")
        return None

    show_details = data.get("ShowDetails", [])
    if not show_details:
        return {}

    api_date = show_details[0].get("Date")
    if str(api_date) != str(DATE_CODE):
        print(f"⏩ Skipping summary for {venue_code} (date mismatch: {api_date} vs {DATE_CODE})")
        return {}

    venue_info = show_details[0].get("Venues", {})
    if not venue_info:
        return {}

    venue_name = venue_info.get("VenueName", "")
    venue_add = venue_info.get("VenueAdd", "")
    shows_by_movie = defaultdict(list)

    for event in data.get("ShowDetails", [{}])[0].get("Event", []):
        parent_title = event.get("EventTitle", "Unknown")
        parent_event_code = event.get("EventGroup") or event.get("EventCode")

        for child in event.get("ChildEvents", []):
            dimension = child.get("EventDimension", "").strip()
            language = child.get("EventLanguage", "").strip()
            child_event_code = child.get("EventCode")

            parts = []
            if dimension:
                parts.append(dimension)
            if language:
                parts.append(language)
            extra_info = " | ".join(parts)
            movie_title = f"{parent_title} [{extra_info}]" if extra_info else parent_title

            for show in child.get("ShowTimes", []):
                total = sold = available = gross = 0
                for cat in show.get("Categories", []):
                    seats = int(cat.get("MaxSeats", 0))
                    avail = int(cat.get("SeatsAvail", 0))
                    price = float(cat.get("CurPrice", 0))
                    total += seats
                    available += avail
                    sold += seats - avail
                    gross += (seats - avail) * price

                show_record = {
                    "venue_code": venue_code,
                    "venue": venue_name,
                    "address": venue_add,
                    "city": ALL_VENUES.get(venue_code, {}).get("City", "Unknown"),
                    "state": ALL_VENUES.get(venue_code, {}).get("State", "Unknown"),
                    "chain": ALL_VENUES.get(venue_code, {}).get("VenueCompName", "Unknown"),
                    "movie": movie_title,
                    "parent_event_code": parent_event_code,
                    "child_event_code": child_event_code,
                    "dimension": dimension,
                    "language": language,
                    "time": show.get("ShowTime"),
                    "session_id": show.get("SessionId"),
                    "audi": show.get("Attributes", ""),
                    "total": total,
                    "sold": sold,
                    "available": available,
                    "occupancy": round((sold / total * 100), 2) if total else 0,
                    "gross": gross,
                }

                shows_by_movie[movie_title].append(show_record)

                # Append to global ALL_SHOWS  # NEW 
                if parent_event_code == "EG00376057":  # They Call Him OG - EG00376057
                    ALL_SHOWS.append(show_record)

    return shows_by_movie


# ---------------- SUMMARY ----------------
def compile_summary(all_data, venues_info):
    movie_stats = {}

    for venue_code, movies in all_data.items():
        venue_meta = venues_info.get(venue_code, {})
        city = venue_meta.get("City", "Unknown")
        state = venue_meta.get("State", "Unknown")

        for movie, shows in movies.items():
            if movie not in movie_stats:
                movie_stats[movie] = {
                    "shows": 0,
                    "gross": 0.0,
                    "sold": 0,
                    "fastfilling": 0,
                    "housefull": 0,
                    "totalSeats": 0,
                    "venues": 0,
                    "details": [],  # <-- array instead of dict
                }

            # search for existing city/state bucket
            city_obj = next(
                (
                    c
                    for c in movie_stats[movie]["details"]
                    if c["city"] == city and c["state"] == state
                ),
                None,
            )

            if not city_obj:
                city_obj = {
                    "city": city,
                    "state": state,
                    "shows": 0,
                    "gross": 0.0,
                    "sold": 0,
                    "totalSeats": 0,
                    "fastfilling": 0,
                    "housefull": 0,
                }
                movie_stats[movie]["details"].append(city_obj)

            # add venue count once per venue
            movie_stats[movie]["venues"] += 1

            for show in shows:
                occ = show["occupancy"]

                # overall
                movie_stats[movie]["shows"] += 1
                movie_stats[movie]["gross"] += show["gross"]
                movie_stats[movie]["sold"] += show["sold"]
                movie_stats[movie]["totalSeats"] += show["total"]

                if occ >= 98:
                    movie_stats[movie]["housefull"] += 1
                elif occ >= 50:
                    movie_stats[movie]["fastfilling"] += 1

                # city-level
                city_obj["shows"] += 1
                city_obj["gross"] += show["gross"]
                city_obj["sold"] += show["sold"]
                city_obj["totalSeats"] += show["total"]

                if occ >= 98:
                    city_obj["housefull"] += 1
                elif occ >= 50:
                    city_obj["fastfilling"] += 1

    return movie_stats


# ---------------- PROGRESS ----------------
def dump_progress(all_data, fetched_venues):
    # Load existing summary if present
    if os.path.exists("movie_summary.json"):
        with open("movie_summary.json", "r", encoding="utf-8") as f:
            try:
                movie_summary = json.load(f)
            except:
                movie_summary = {}
    else:
        movie_summary = {}

    # Load venues info for city/state mapping
    if os.path.exists("venues.json"):
        with open("venues.json", "r", encoding="utf-8") as f:
            venues_info = json.load(f)
    else:
        venues_info = {}

    # Load already processed venues
    if os.path.exists("processed_venues.json"):
        with open("processed_venues.json", "r", encoding="utf-8") as f:
            try:
                processed_venues = set(json.load(f))
            except:
                processed_venues = set()
    else:
        processed_venues = set()

    # --- Process only NEW venues ---
    new_venues = set(fetched_venues) - processed_venues

    for vcode in new_venues:
        venue_meta = venues_info.get(vcode, {})
        city = venue_meta.get("City", "Unknown")
        state = venue_meta.get("State", "Unknown")

        for movie, shows in all_data.get(vcode, {}).items():
            if movie not in movie_summary:
                movie_summary[movie] = {
                    "shows": 0,
                    "gross": 0.0,
                    "sold": 0,
                    "totalSeats": 0,
                    "venues": 0,
                    "cities": 0,
                    "fastfilling": 0,
                    "housefull": 0,
                    "occupancy": 0.0,
                    "details": [],
                    "Chain_details": [],
                }

            # --- Update top-level movie stats ---
            movie_summary[movie]["venues"] += 1
            for show in shows:
                sold = show["sold"]
                total = show["total"]
                occ = (sold / total * 100) if total > 0 else 0

                movie_summary[movie]["shows"] += 1
                movie_summary[movie]["gross"] += show["gross"]
                movie_summary[movie]["sold"] += sold
                movie_summary[movie]["totalSeats"] += total

                if 50 <= occ < 98:
                    movie_summary[movie]["fastfilling"] += 1
                elif occ >= 98:
                    movie_summary[movie]["housefull"] += 1

            # --- Update city/state level ---
            city_block = None
            for d in movie_summary[movie]["details"]:
                if d["city"] == city and d["state"] == state:
                    city_block = d
                    break

            if city_block is None:
                city_block = {
                    "city": city,
                    "state": state,
                    "venues": 0,
                    "shows": 0,
                    "gross": 0.0,
                    "sold": 0,
                    "totalSeats": 0,
                    "fastfilling": 0,
                    "housefull": 0,
                    "occupancy": 0.0,
                }
                movie_summary[movie]["details"].append(city_block)
                movie_summary[movie]["cities"] += 1  # new city found

            city_block["venues"] += 1

            for show in shows:
                sold = show["sold"]
                total = show["total"]
                occ = (sold / total * 100) if total > 0 else 0

                city_block["shows"] += 1
                city_block["gross"] += show["gross"]
                city_block["sold"] += sold
                city_block["totalSeats"] += total

                if 50 <= occ < 98:
                    city_block["fastfilling"] += 1
                elif occ >= 98:
                    city_block["housefull"] += 1

            if city_block["totalSeats"] > 0:
                city_block["occupancy"] = round(
                    city_block["sold"] / city_block["totalSeats"] * 100, 2
                )

            # --- Update chain-level ---
            chain = shows[0].get("chain", "Unknown")
            chain_block = None
            for d in movie_summary[movie]["Chain_details"]:
                if d["chain"] == chain:
                    chain_block = d
                    break

            if chain_block is None:
                chain_block = {
                    "chain": chain,
                    "venues": 0,
                    "shows": 0,
                    "gross": 0.0,
                    "sold": 0,
                    "totalSeats": 0,
                    "fastfilling": 0,
                    "housefull": 0,
                    "occupancy": 0.0,
                }
                movie_summary[movie]["Chain_details"].append(chain_block)

            chain_block["venues"] += 1

            for show in shows:
                sold = show["sold"]
                total = show["total"]
                occ = (sold / total * 100) if total > 0 else 0

                chain_block["shows"] += 1
                chain_block["gross"] += show["gross"]
                chain_block["sold"] += sold
                chain_block["totalSeats"] += total

                if 50 <= occ < 98:
                    chain_block["fastfilling"] += 1
                elif occ >= 98:
                    chain_block["housefull"] += 1

            if chain_block["totalSeats"] > 0:
                chain_block["occupancy"] = round(
                    chain_block["sold"] / chain_block["totalSeats"] * 100, 2
                )

    # --- Update movie-level occupancy after processing ---
    for movie, data in movie_summary.items():
        if data["totalSeats"] > 0:
            data["occupancy"] = round(data["sold"] / data["totalSeats"] * 100, 2)
        else:
            data["occupancy"] = 0.0

        if "details" in data:
            data["details"] = sorted(
                data["details"], key=lambda x: x["gross"], reverse=True
            )

    # --- Save updated movie summary ---
    with open("movie_summary.json.tmp", "w", encoding="utf-8") as f:
        json.dump(movie_summary, f, indent=2, ensure_ascii=False)
    os.replace("movie_summary.json.tmp", "movie_summary.json")

    # --- Save fetched venues ---
    with open("fetchedvenues.json.tmp", "w", encoding="utf-8") as f:
        json.dump(list(fetched_venues), f, indent=2)
    os.replace("fetchedvenues.json.tmp", "fetchedvenues.json")

    # --- Save processed venues ---
    processed_venues |= new_venues
    with open("processed_venues.json.tmp", "w", encoding="utf-8") as f:
        json.dump(list(processed_venues), f, indent=2)
    os.replace("processed_venues.json.tmp", "processed_venues.json")

    # --- Save ALL_SHOWS snapshot (new) ---
    with open("all_shows.json.tmp", "w", encoding="utf-8") as f:
        json.dump(ALL_SHOWS, f, indent=2, ensure_ascii=False)
    os.replace("all_shows.json.tmp", "all_shows.json")

    print(
        f"💾 Progress dumped. Venues: {len(fetched_venues)} "
        f"(New added: {len(new_venues)}), Shows saved: {len(ALL_SHOWS)}"
    )


# ---------------- FETCH SAFE ----------------
def fetch_venue_safe(venue_code):
    global error_count
    with lock:
        if venue_code in fetched_venues:
            return

    data = fetch_data(venue_code)
    if data is None:  # real error
        with lock:
            error_count += 1
            if error_count >= MAX_ERRORS:
                print("🛑 Too many errors. Restarting...")
                dump_progress(all_data, fetched_venues)
                time.sleep(0.5)
                os.execv(sys.executable, ["python"] + sys.argv)
    else:
        with lock:
            if venue_code not in all_data:
                all_data[venue_code] = {}
            # Only add to summary if non-empty
            if data:
                for movie, shows in data.items():
                    all_data[venue_code][movie] = shows
            fetched_venues.add(venue_code)
            print(
                f"✅ Successfully fetched venue: {venue_code} ({len(fetched_venues)} fetched so far)"
            )
            dump_progress(all_data, fetched_venues)


# ---------------- MAIN ----------------
if __name__ == "__main__":
    with open("venues.json", "r", encoding="utf-8") as f:
        venues = json.load(f)

    if os.path.exists("fetchedvenues.json"):
        with open("fetchedvenues.json", "r", encoding="utf-8") as f:
            fetched_venues = set(json.load(f))
    else:
        fetched_venues = set()

    if os.path.exists("venues_data.json"):
        with open("venues_data.json", "r", encoding="utf-8") as f:
            try:
                all_data = json.load(f)
            except:
                all_data = {}
    else:
        all_data = {}

    print(
        f"🚀 Starting fetch with {NUM_WORKERS} workers. Already fetched: {len(fetched_venues)} venues"
    )

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(fetch_venue_safe, vcode) for vcode in venues.keys()]
        for _ in as_completed(futures):
            pass

    # Instead, load the final updated movie_summary.json
    with open("movie_summary.json", "r", encoding="utf-8") as f:
        movie_summary = json.load(f)

    df = pd.DataFrame([{"Movie": k, **v} for k, v in movie_summary.items()])
    df = df.sort_values(by="gross", ascending=False).reset_index(drop=True)
    df.to_csv("movie_summary.csv", index=False)

    def pretty_divider(title=""):
        line = "─" * 25
        if title:
            print(f"\n{line} ✦ {title} ✦ {line}\n")
        else:
            print(f"\n{line} ✦ {line}\n")

    # ------------------------------------------------------
    # Language-wise Summary
    # ------------------------------------------------------
    pretty_divider("Language-wise Summary")

    console_rows = []
    lang_summary = {}

    for movie, stats in movie_summary.items():
        # Split "Title [Dimension | Language]" back into title + language
        if "[" in movie and "|" in movie:
            base_title = movie.split("[")[0].strip()
            lang = movie.split("|")[-1].replace("]", "").strip()
        else:
            base_title = movie.strip()
            lang = "Unknown"

        key = (base_title, lang)

        if key not in lang_summary:
            lang_summary[key] = {"shows": 0, "gross": 0.0, "sold": 0, "totalSeats": 0}

        lang_summary[key]["shows"] += stats["shows"]
        lang_summary[key]["gross"] += stats["gross"]
        lang_summary[key]["sold"] += stats["sold"]
        lang_summary[key]["totalSeats"] += stats["totalSeats"]

    for (title, lang), stats in lang_summary.items():
        occ = (
            round(stats["sold"] / stats["totalSeats"] * 100, 2)
            if stats["totalSeats"]
            else 0
        )
        atp = round(stats["gross"] / stats["sold"], 2) if stats["sold"] else 0
        rgross = format_rgross(stats["gross"])
        console_rows.append(
            {
                "Movie (Lang)": f"{title} ({lang})",
                "Shows": stats["shows"],
                "Gross": round(stats["gross"], 2),
                "Sold": stats["sold"],
                "TotalSeats": stats["totalSeats"],
                "ATP": atp,
                "Occ%": occ,
                "RGross": rgross,
            }
        )

    df_console = pd.DataFrame(console_rows)
    df_console = df_console.sort_values(by="Gross", ascending=False).reset_index(
        drop=True
    )
    print(df_console.to_string(index=False))

    # ------------------------------------------------------
    # Movie-wise Summary
    # ------------------------------------------------------
    pretty_divider("Movie-wise Summary")

    movie_only_rows = []
    movie_only_summary = {}

    for movie, stats in movie_summary.items():
        if "[" in movie:
            base_title = movie.split("[")[0].strip()
        else:
            base_title = movie.strip()

        if base_title not in movie_only_summary:
            movie_only_summary[base_title] = {
                "shows": 0,
                "gross": 0.0,
                "sold": 0,
                "totalSeats": 0,
            }

        movie_only_summary[base_title]["shows"] += stats["shows"]
        movie_only_summary[base_title]["gross"] += stats["gross"]
        movie_only_summary[base_title]["sold"] += stats["sold"]
        movie_only_summary[base_title]["totalSeats"] += stats["totalSeats"]

    for title, stats in movie_only_summary.items():
        occ = (
            round(stats["sold"] / stats["totalSeats"] * 100, 2)
            if stats["totalSeats"]
            else 0
        )
        atp = round(stats["gross"] / stats["sold"], 2) if stats["sold"] else 0
        rgross = format_rgross(stats["gross"])
        movie_only_rows.append(
            {
                "Movie": title,
                "Shows": stats["shows"],
                "Gross": round(stats["gross"], 2),
                "Sold": stats["sold"],
                "TotalSeats": stats["totalSeats"],
                "ATP": atp,
                "Occ%": occ,
                "RGross": rgross,
            }
        )

    df_movie_only = pd.DataFrame(movie_only_rows)
    df_movie_only = df_movie_only.sort_values(by="Gross", ascending=False).reset_index(
        drop=True
    )
    print(df_movie_only.to_string(index=False))
    pretty_divider("Format & Language-wise Summary")

    print("✅ Movie summary saved to movie_summary.csv")
    dump_progress(all_data, fetched_venues)
    print("✅ Final progress saved.")

