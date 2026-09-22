
import pandas as pd
import requests
import streamlit as st

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FBref Advanced Stats Hub", page_icon="⚽", layout="wide"
)

st.title("⚽ FBref Advanced Premier League Analytics")
st.markdown(
    "Standalone dashboard for FBref underlying stats: **Shooting, Passing,"
    " Shot/Goal Creation (SCA/GCA), and Defensive Actions**."
)

# --- 2. SEASON & METRIC SELECTOR ---
SEASON_MAPPING = {
    "2025/26 (Current)": "2025-2026",
    "2024/25": "2024-2025",
    "2023/24": "2023-2024",
    "2022/23": "2022-2023",
}

STAT_TYPES = {
    "Standard Stats": "stats",
    "Shooting": "shooting",
    "Passing": "passing",
    "Goal & Shot Creation (SCA)": "gca",
    "Defensive Actions": "defense",
    "Possession & Carries": "possession",
}

st.sidebar.header("⚙️ Controls")
selected_season_label = st.sidebar.selectbox(
    "Select Season", options=list(SEASON_MAPPING.keys()), index=0
)
selected_season = SEASON_MAPPING[selected_season_label]

selected_stat_label = st.sidebar.selectbox(
    "Select Stat Category", options=list(STAT_TYPES.keys()), index=0
)
stat_category = STAT_TYPES[selected_stat_label]

if st.sidebar.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Real browser headers to maximize Cloudflare bypass rate
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
}


# --- 3. FBREF FETCH ENGINE ---
@st.cache_data(ttl=1800)
def fetch_fbref_category(season_str, category):
    """Fetches and parses standard FBref tabular stat pages."""
    url = f"https://fbref.com/en/comps/9/{season_str}/{category}/squads/Premier-League-Stats"

    try:
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=12)

        if response.status_code == 403:
            st.error(
                "⚠️ **FBref Access Blocked (HTTP 403)**: Cloudflare has"
                " temporarily rate-limited Streamlit Cloud's IP. Wait 2-3"
                " minutes and hit 'Force Refresh Data'."
            )
            return None
        elif response.status_code != 200:
            st.error(
                f"⚠️ FBref returned status code {response.status_code} for URL:"
                f" {url}"
            )
            return None

        # Parse tables using Pandas HTML parser
        tables = pd.read_html(response.text)
        if not tables:
            return None

        df = tables[0]

        # Flatten multi-index headers if Present
        if isinstance(df.columns, pd.MultiIndex):
            new_cols = []
            for col in df.columns:
                top, bottom = str(col[0]), str(col[1])
                if "Unnamed" in top or top == bottom:
                    new_cols.append(bottom)
                else:
                    new_cols.append(f"{top}_{bottom}")
            df.columns = new_cols

        # Clean duplicate summary rows
        player_cols = [c for c in df.columns if "player" in c.lower()]
        if player_cols:
            p_col = player_cols[0]
            df = df[df[p_col].astype(str) != "Player"]
            df = df[~df[p_col].isna()]

        return df

    except Exception as e:
        st.error(f"⚠️ Failed to connect to FBref: {e}")
        return None


# --- 4. APP RENDER ---
with st.spinner(f"Loading {selected_stat_label} from FBref..."):
    df_fbref = fetch_fbref_category(selected_season, stat_category)

if df_fbref is not None and not df_fbref.empty:
    st.subheader(
        f"📋 {selected_stat_label} — {selected_season_label} ({len(df_fbref)}"
        " rows)"
    )

    # Search / Filter Bar
    search_query = st.text_input("🔍 Search Player or Squad", "")
    if search_query:
        # Match string across any text column
        mask = df_fbref.astype(str).apply(
            lambda x: x.str.contains(search_query, case=False, na=False)
        )
        filtered_df = df_fbref[mask.any(axis=1)]
    else:
        filtered_df = df_fbref

    st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning(
        "No data available to display right now. If FBref is blocking the"
        " connection, try clicking **Force Refresh Data** in a few moments."
    )
