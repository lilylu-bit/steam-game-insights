import sqlite3
import pandas as pd

# Example: load your existing CSV
df = pd.read_csv("../data/processed/steam_master.csv")

# Create/connect to database file
conn = sqlite3.connect("../data/db/steam_master.db")

# Save dataframe into database table
df.to_sql("steam_games", conn, if_exists="replace", index=False)

# Close connection
conn.close()

print("✅ Database created!")

conn = sqlite3.connect("../data/db/steam_master.db")

df_check = pd.read_sql("SELECT * FROM steam_games LIMIT 5", conn)

print(df_check)

conn.close()