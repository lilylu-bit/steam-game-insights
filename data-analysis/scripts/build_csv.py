import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect("../data/db/steam_master.db")
df = pd.read_sql("SELECT * FROM steam_games", conn)
conn.close()

# Save master CSV
df.to_csv("../data/processed/steam_master.csv", index=False)

# Prepare Tableau version (explode genres)
SPECIAL_TAGS = {"Indie", "Free To Play", "Early Access"}

# Split into lists once, cleanly
genres_list     = df["genres"].fillna("").str.split("|")
categories_list = df["categories"].fillna("").str.split("|")

# Boolean columns from genres
df["indie"]        = genres_list.apply(lambda tags: int("Indie" in tags))
df["free_to_play"] = genres_list.apply(lambda tags: int("Free To Play" in tags))
df["early_access"] = genres_list.apply(lambda tags: int("Early Access" in tags))

# Boolean columns from categories
df["singleplayer"] = categories_list.apply(lambda cats: int("Single-player" in cats))
df["multiplayer"]  = categories_list.apply(lambda cats: int("Multi-player" in cats))

# Build genre column for exploding — filter special tags out here, separately
df["genre"] = genres_list.apply(lambda tags: [t for t in tags if t not in SPECIAL_TAGS])

# Explode into one row per genre
df_exploded = df.explode("genre")

# Drop categories column (too granular for Tableau)
df_exploded = df_exploded.drop(columns=["genres", "categories"])

df_exploded.to_csv("../data/processed/steam_tableau.csv", index=False)
print("Processed CSV built from database")