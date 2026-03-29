import streamlit as st
import pandas as pd
import time
from datetime import datetime

# Import backend modules
from config import APP_TITLE, APP_ICON, UI_COLORS, TEAM_ABBR_TO_NAME, PARLAY_CONFIG
from data_fetcher import get_games_for_date, generate_demo_games
from team_analysis import get_full_team_analysis
from player_analysis import get_full_player_analysis
from analytics_engine import generate_game_analysis
from betting_intelligence import get_all_bets_for_game
from parlay_engine import generate_parlays, format_parlay_for_display
from odds_api import fetch_live_odds, apply_live_odds
from ui_components import render_matchup_deep_dive

# ─── Page Configuration ───────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Session State Initialization ─────────────────────────────────────
if "selected_game_id" not in st.session_state:
    st.session_state.selected_game_id = None
if "all_bets_by_game" not in st.session_state:
    st.session_state.all_bets_by_game = {}
if "game_analyses" not in st.session_state:
    st.session_state.game_analyses = {}
if "games" not in st.session_state:
    st.session_state.games = []

# ─── Custom CSS ───────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@500;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {UI_COLORS['bg_primary']}; color: {UI_COLORS['text_primary']}; }}
    
    h1 {{
        font-family: 'Outfit', sans-serif !important; font-weight: 800 !important;
        background: linear-gradient(135deg, {UI_COLORS['accent']}, {UI_COLORS['accent_secondary']});
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;
    }}
    
    [data-testid="metric-container"] {{
        background: {UI_COLORS['bg_card']} !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid {UI_COLORS['border']} !important;
        border-radius: 12px !important; padding: 20px !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    }}
    [data-testid="metric-container"]:hover {{
        transform: translateY(-4px) !important; border-color: rgba(0, 212, 170, 0.4) !important;
    }}
    
    .stButton > button {{
        background: linear-gradient(135deg, {UI_COLORS['accent']}, #00A383);
        color: #fff !important; font-weight: 600 !important; border-radius: 8px !important; border: none !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ─── Sidebar Configuration ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Settings")
        
        st.markdown("### Risk Management")
        risk_pref = st.selectbox(
            "Risk Preference", 
            ["ultra_safe", "low", "balanced"],
            format_func=lambda x: x.replace("_", " ").title(),
            index=1
        )
        
        parlay_legs = st.slider("Parlay Legs", min_value=4, max_value=8, value=4)
        
        st.markdown("### Live Odds API")
        api_key = st.text_input("The-Odds-API Key", type="password", help="Paste your key to fetch real-time bookmaker lines.")
        
        st.markdown("### Data Source")
        game_date = st.date_input("Game Date", datetime.now().date(), help="Select the scheduled day of the NBA games.")
        use_demo = st.checkbox("Use Demo Data (Fallback)", value=False)
        
        if st.button("Refresh / Fetch Data 🔄", use_container_width=True):
            fetch_and_analyze(use_demo, api_key, game_date)
            
        st.divider()
        st.caption("Auto-refresh supported by manually re-clicking Fetch Data above.")
        
        return risk_pref, parlay_legs, api_key, use_demo, game_date

# ─── Backend Data Pipeline ─────────────────────────────────────────────
def fetch_and_analyze(use_demo, api_key, game_date):
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    
    with status_placeholder.container():
        st.info("Fetching game schedules and injury reports...")
    
    if use_demo:
        games = generate_demo_games()
    else:
        games = get_games_for_date(game_date)
        if not games:
            status_placeholder.warning("No live games found for selected date. Falling back to Demo Game Analytics.")
            games = generate_demo_games()
            
    st.session_state.games = games
    st.session_state.all_bets_by_game = {}
    st.session_state.game_analyses = {}
    
    total_games = len(games)
    
    # Optional Live odds
    live_odds_map = fetch_live_odds(api_key) if api_key else {}

    for i, game in enumerate(games):
        home_abbr = game.get("home_team_abbr", "Home")
        away_abbr = game.get("away_team_abbr", "Away")
        
        with status_placeholder.container():
            st.info(f"Analyzing Matchup: **{away_abbr} @ {home_abbr}**... ")
        
        home_id = game["home_team_id"]
        away_id = game["away_team_id"]
        
        try:
            home_team_analysis = get_full_team_analysis(home_id, away_id, is_home=True)
            away_team_analysis = get_full_team_analysis(away_id, home_id, is_home=False)
            home_players = get_full_player_analysis(home_id)
            away_players = get_full_player_analysis(away_id)
            
            game_analysis = generate_game_analysis(game, home_team_analysis, away_team_analysis, home_players, away_players)
            bets = get_all_bets_for_game(game_analysis)
            
            # Blend live odds into the statistical estimation if provided
            if live_odds_map:
                bets = apply_live_odds(bets, live_odds_map, TEAM_ABBR_TO_NAME)
                
            st.session_state.game_analyses[game["game_id"]] = game_analysis
            st.session_state.all_bets_by_game[game["game_id"]] = bets
            
        except Exception as e:
            st.toast(f"Error processing {away_abbr} @ {home_abbr}: {e}", icon="⚠️")
            
        progress_bar.progress((i + 1) / total_games)
        
    status_placeholder.success("Analysis complete! Check the Matchups and Parlay Generator.")
    time.sleep(1)
    status_placeholder.empty()
    progress_bar.empty()


# ─── Application View ──────────────────────────────────────────────────
def render_todays_games():
    st.header("Scores & Matchups")
    if not st.session_state.games:
        st.info("Click **Refresh / Fetch Data** in the sidebar to load games.")
        return
        
    cols = st.columns(3)
    for i, game in enumerate(st.session_state.games):
        col = cols[i % 3]
        with col:
            st.markdown(f"### {game['away_team_abbr']} @ {game['home_team_abbr']}")
            st.caption(game.get('game_status_text', 'Scheduled'))
            if st.button(f"Analyze Matchup", key=f"btn_{game['game_id']}"):
                st.session_state.selected_game_id = game['game_id']
                st.toast(f"Matchup {game['away_team_abbr']} @ {game['home_team_abbr']} selected! Click the 'Matchup Deep Dive' tab.", icon="📊")
                time.sleep(1) # Give user a second to read before rerun clears toast
                st.rerun()

def main():
    inject_custom_css()
    
    st.title("🏀 NBA Parlay Generator")
    risk_pref, parlay_legs, api_key, use_demo, game_date = render_sidebar()
    
    tab1, tab2, tab3 = st.tabs(["📊 Today's Games", "🔬 Matchup Deep Dive", "🎯 Parlay Generator"])
    
    with tab1:
        render_todays_games()
        
    with tab2:
        if st.session_state.selected_game_id and st.session_state.selected_game_id in st.session_state.game_analyses:
            render_matchup_deep_dive(
                st.session_state.selected_game_id, 
                st.session_state.all_bets_by_game, 
                st.session_state.game_analyses
            )
        else:
            st.info("Select 'Analyze Matchup' from the Today's Games tab to view deep dive stats.")

    with tab3:
        st.header("Recommended Parlays")
        if not st.session_state.all_bets_by_game:
            st.info("Please fetch data first.")
        else:
            # Enforce 4-8 leg config
            PARLAY_CONFIG['min_legs'] = parlay_legs
            PARLAY_CONFIG['max_legs'] = parlay_legs
            
            parlays = generate_parlays(st.session_state.all_bets_by_game, risk_preference=risk_pref)
            
            if not parlays:
                st.warning(f"No {parlay_legs}-leg parlay combinations found matching the strict '{risk_pref}' risk requirements.", icon="⚠️")
            else:
                for idx, p in enumerate(parlays):
                    formatted = format_parlay_for_display(p, rank=idx+1)
                    
                    st.markdown(f"<h2>{formatted['title']} — {formatted['subtitle']} {formatted['risk_emoji']}</h2>", unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Odds", formatted["combined_odds"])
                    col2.metric("Hit Probability", f"{formatted['probability']*100:.1f}%")
                    col3.metric("System Confidence", f"{formatted['confidence']}/100")
                    col4.metric("Expected Value (+)", f"{formatted['expected_value']:.2f}")
                    
                    st.markdown(f"<p style='color: {UI_COLORS['text_secondary']}; margin-top: 5px; margin-bottom: 20px;'><i>{formatted['description']}</i></p>", unsafe_allow_html=True)
                    
                    st.markdown("#### Parlay Legs")
                    for leg in formatted["legs"]:
                        st.markdown(f"""
                        <div style="background-color: {UI_COLORS['bg_secondary']}; border-left: 4px solid {UI_COLORS['accent_secondary']}; padding: 12px 16px; margin-bottom: 10px; border-radius: 4px 8px 8px 4px;">
                            <div><b><span style="font-size: 1.2em; margin-right: 8px;">{leg.get('bet_icon', '🏀')}</span> {leg['bet_label']}</b></div>
                            <div style="color: {UI_COLORS['text_secondary']}; font-size: 0.9em; margin-top: 4px;">{leg['explanation']}</div>
                            <div style="font-size: 0.85em; font-weight: 600; margin-top: 4px; color: {UI_COLORS['accent']};">Implied Prob: {leg['probability']*100:.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.divider()

if __name__ == "__main__":
    main()
