import pandas as pd
import requests
import streamlit as st

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FotMob Premier League Analytics", page_icon="⚡", layout="wide"
)

st.title("⚡ Premier League Advanced Stats (FotMob / Opta Data)")
st.markdown(
    "Direct live feed from FotMob's Opta data endpoints. Includes **xG, xA,"
    " Big Chances, Key Passes, and Box Touches**."
)

# --- 2. STAT CATEGORY MAPPING ---
# FotMob internal stat keys for Premier League (League ID: 47)
STAT_CATEGORIES = {
    "Expected Goals (xG)": "expected_goals",
    "Expected Assists (xA)": "expected_assists",
    "Goals + Assists": "goals_and_assists",
    "Total Shots": "total_shots",
    "Shots on Target": "shots_on_target",
    "Big Chances Created": "big_chance_created",
    "Accurate Passes": "accurate_passes",
}

st.sidebar.header("⚙️ Controls")
selected_stat_label = st.sidebar.selectbox(
    "Select Metric Leaderboard", options=list(STAT_CATEGORIES.keys()), index=0
)
stat_type = STAT_CATEGORIES[selected_stat_label]

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()


# --- 3. FOTMOB DATA FETCH ENGINE ---
@st.cache_data(ttl=900)
def fetch_fotmob_leaderboard(stat_key):
    """Fetches category leaderboards directly from FotMob API without blocking."""
    url = f"https://www.fotmob.com/api/leagueseasonstats?id=47&season=2025/2026&type=players&stat={stat_key}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ),
        "Accept": "application/json",
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()

            # Parse player stats array
            stats_list = data.get("statsData", [])
            parsed_rows = []

            for entry in stats_list:
                parsed_rows.append({
                    "Player": entry.get("name"),
                    "Team": entry.get("teamName"),
                    "Stat Value": entry.get("statValue"),
                    "SubStat / Per90": entry.get("subStatValue"),
                    "Matches Played": entry.get("matchesStarted", 0)
                    + entry.get("matchesSubbedOn", 0),
                })

            return pd.DataFrame(parsed_rows)
        else:
            st.error(
                f"FotMob API returned status {res.status_code}. Try again in a"
                " moment."
            )
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching FotMob data: {e}")
        return pd.DataFrame()


# --- 4. RENDER APP ---
with st.spinner(f"Loading {selected_stat_label} from FotMob..."):
    df_fotmob = fetch_fotmob_leaderboard(stat_type)

if not df_fotmob.empty:
    st.subheader(
        f"📋 Leaderboard: {selected_stat_label} ({len(df_fotmob)} Players)"
    )

    # Search Bar
    search_query = st.text_input("🔍 Search Player or Team", "")
    if search_query:
        mask = df_fotmob.astype(str).apply(
            lambda x: x.str.contains(search_query, case=False, na=False)
        )
        filtered_df = df_fotmob[mask.any(axis=1)]
    else:
        filtered_df = df_fotmob

    st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning("No data retrieved for this stat category.")
