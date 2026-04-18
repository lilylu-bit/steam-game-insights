import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
MAX_GAMES_BESTSELLERS = 500
MAX_GAMES_NEWRELEASES = 100
DELAY = (1, 3)  # random delay to avoid blocks
CSV_FILE_TEMPLATE = "../data/raw/steam_games_{date}.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}


# -----------------------------
# STEP 1: GET APP IDS FROM BESTSELLERS
# -----------------------------
def get_appids_bestsellers(max_games=500):
    appids = []
    page = 1
    current_rank = 1

    while len(appids) < max_games:
        url = f"https://store.steampowered.com/search/?filter=topsellers&page={page}"
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select("a.search_result_row")

        if not links:
            break

        print(f"Best Sellers - Page {page}: Processing {len(links)} items...")

        for link in links:
            appid = link.get("data-ds-appid")
            # Only count and add if it's a game (has an appid)
            # This automatically skips bundles without skipping rank numbers
            if appid:
                appids.append({
                    "appid": int(appid),
                    "rank_type": "topsellers",
                    "rank_position": current_rank
                })
                current_rank += 1

            if len(appids) >= max_games:
                break

        page += 1
        time.sleep(random.uniform(*DELAY))

    return appids

# -----------------------------
# STEP 2: GET APP IDS FROM NEW RELEASES
# -----------------------------
def get_appids_newreleases(max_games=100):
    appids = []
    page = 1
    current_rank = 1
    seen = set()

    # Use the specific Popular New Releases URL with your filters
    base_url = "https://store.steampowered.com/search/?filter=popularnew&sort_by=Released_DESC&os=win"

    while len(appids) < max_games:
        url = f"{base_url}&page={page}"
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        # Target the main search rows only
        links = soup.select("a.search_result_row")

        if not links:
            print("No more results found or blocked.")
            break

        print(f"Popular New - Page {page}: Found {len(links)} items")

        for link in links:
            appid = link.get("data-ds-appid")
            if appid and appid not in seen:
                seen.add(appid)
                appids.append({
                    "appid": int(appid),
                    "rank_type": "popularnew",
                    "rank_position": current_rank
                })
                current_rank += 1

            if len(appids) >= max_games:
                break

        page += 1
        time.sleep(random.uniform(*DELAY))

    print(f"Total Popular New Releases collected: {len(appids)}")
    return appids

# -----------------------------
# STEP 3: FETCH GAME DETAILS
# -----------------------------
def fetch_game_details(appid, rank_type=None, rank_position=None):
    try:
        # Game info
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"
        r = requests.get(url, headers=HEADERS)
        data = r.json()
        game = data.get(str(appid), {})
        if not game.get("success"):
            return None
        info = game.get("data", {})

        developers = "|".join(info.get("developers", [])) if info.get("developers") else None
        publishers = "|".join(info.get("publishers", [])) if info.get("publishers") else None
        genres = "|".join([g["description"] for g in info.get("genres", [])]) if info.get("genres") else None
        categories = "|".join([c["description"] for c in info.get("categories", [])]) if info.get(
            "categories") else None
        price = info.get("price_overview", {}).get("final_formatted") if info.get("price_overview") else "Free"
        item_type = info.get("type")

        # User review percentages
        # Total reviews
        review_url_total = f"https://store.steampowered.com/appreviews/{appid}?json=1&num_per_page=1&purchase_type=all&filter=all"
        r_total = requests.get(review_url_total, headers=HEADERS)
        query_total = r_total.json().get("query_summary", {})
        user_positive_total = query_total.get("total_positive", 0)
        user_total_total = query_total.get("total_reviews", 0)
        if user_total_total > 0:
            user_positive_percent_total = round(user_positive_total / user_total_total * 100, 2)
        else:
            user_positive_percent_total = None

        return {
            "appid": appid,
            "title": info.get("name"),
            "item_type": item_type,
            "release_date": info.get("release_date", {}).get("date"),
            "developer": developers,
            "publisher": publishers,
            "genres": genres,
            "categories": categories,
            "price": price,
            "user_positive_total": user_positive_percent_total,
            "rank_type": rank_type,
            "rank_position": rank_position,
            "timestamp": datetime.today().strftime("%Y-%m-%d")
        }

    except Exception as e:
        print(f"Error with appid {appid}: {e}")
        return None


# -----------------------------
# STEP 4: MAIN PIPELINE
# -----------------------------
def main():
    today_str = datetime.today().strftime("%Y%m%d")
    CSV_FILE = CSV_FILE_TEMPLATE.format(date=today_str)

    all_appids = []
    all_appids.extend(get_appids_bestsellers(MAX_GAMES_BESTSELLERS))
    all_appids.extend(get_appids_newreleases(MAX_GAMES_NEWRELEASES))

    print(f"Total AppIDs collected: {len(all_appids)}")

    games = []
    for entry in all_appids:
        appid = entry["appid"]
        rank_type = entry.get("rank_type")
        rank_position = entry.get("rank_position")
        print(f"Fetching ({rank_type} {rank_position}/{len(all_appids)}): {appid}")
        game = fetch_game_details(appid, rank_type, rank_position)
        if game:
            games.append(game)
        time.sleep(random.uniform(*DELAY))

    if not games:
        print("No data collected. Exiting.")
        return

    df = pd.DataFrame(games)

    df.to_csv(CSV_FILE, index=False)

    import sqlite3

    # Save to SQLite
    conn = sqlite3.connect("../data/db/steam_master.db")

    df.to_sql("steam_games", conn, if_exists="append", index=False)

    df = df.drop_duplicates(subset=["appid", "timestamp", "rank_type"])

    conn.close()

    print(f"Saved {len(df)} games to {CSV_FILE}")

    # Optional: show top genres
    df["genres_list"] = df["genres"].fillna("").apply(lambda x: x.split("|"))
    exploded = df.explode("genres_list")
    print("\n Top Genres:")
    print(exploded["genres_list"].value_counts().head(10))

if __name__ == "__main__":
    main()