import pandas as pd
import requests
import streamlit as st

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FotMob Premier League Analytics", page_icon="⚡", layout="wide"
)

st.title("⚡ Premier League Advanced Stats (FotMob / Opta Data)")
st.markdown(
    "Direct live feed from FotMob's API. Includes **xG, xA, Big Chances,"
    " Shots on Target, and Key Passes** without scraping blocks."
)

# --- 2. STAT CATEGORY MAPPING ---
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


# --- 3. FOTMOB DATA FETCH ENGINE ---
@st.cache_data(ttl=900)
def fetch_fotmob_leaderboard(stat_key):
    """Fetches player stat leaderboards from FotMob API for the Premier League (ID: 47)."""
    # Using FotMob's general season endpoint structure
    url = f"https://www.fotmob.com/api/leagueseasonstats?id=47&type=players&stat={stat_key}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)

        # Fallback if standard endpoint varies
        if res.status_code == 404:
            url_alt = f"https://www.fotmob.com/api/m/leagueseasonstats?id=47&type=players&stat={stat_key}"
            res = requests.get(url_alt, headers=HEADERS, timeout=10)

        if res.status_code == 200:
            data = res.json()

            # Parse stats array
            stats_list = data.get("statsData", [])
            if not stats_list and "topThree" in data:
                stats_list = data.get("topThree", []) + data.get("all", [])

            parsed_rows = []
            for entry in stats_list:
                parsed_rows.append({
                    "Player": entry.get("name"),
                    "Team": entry.get("teamName"),
                    "Stat Value": entry.get("statValue"),
                    "Per 90 / Detail": entry.get("subStatValue", "-"),
                    "Matches": entry.get("matchesStarted", 0)
                    + entry.get("matchesSubbedOn", 0),
                })

            return pd.DataFrame(parsed_rows)
        else:
            st.error(
                f"FotMob returned status {res.status_code}. The endpoint may"
                " be temporarily unavailable."
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
    st.warning("No data retrieved. Try clicking 'Refresh Data' in the sidebar.")
