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
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📊 Today's Games"

# ─── Custom CSS ───────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@500;700&family=JetBrains+Mono:wght@500&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; transition: all 0.2s ease-in-out; }}
    .stApp {{ background-color: {UI_COLORS['bg_primary']}; color: {UI_COLORS['text_primary']}; }}
    
    /* Header Typography */
    h1 {{
        font-family: 'Outfit', sans-serif !important; font-weight: 800 !important;
        background: linear-gradient(135deg, {UI_COLORS['accent']}, {UI_COLORS['accent_secondary']});
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; letter-spacing: -0.02em;
    }}
    h2, h3 {{ font-family: 'Outfit', sans-serif !important; font-weight: 700 !important; }}
    
    /* Global Glass Card Style */
    .glass-card {{
        background: {UI_COLORS['bg_card']} !important;
        backdrop-filter: blur(16px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(16px) saturate(180%) !important;
        border: 1px solid {UI_COLORS['border']} !important;
        border-radius: 16px !important;
        padding: 24px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
    }}
    
    /* Metric Container Overhaul */
    [data-testid="metric-container"] {{
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important; padding: 16px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    [data-testid="metric-container"]:hover {{
        background: rgba(255, 255, 255, 0.05) !important;
        transform: translateY(-2px) !important; border-color: {UI_COLORS['accent']} !important;
    }}
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: {UI_COLORS['bg_secondary']} !important;
        border-right: 1px solid {UI_COLORS['border']} !important;
    }}
    
    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, {UI_COLORS['accent']}, #00A383);
        color: #fff !important; font-weight: 600 !important; 
        border-radius: 10px !important; border: none !important;
        padding: 0.6rem 1.2rem !important; transition: all 0.3s ease !important;
        text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.85rem !important;
    }}
    .stButton > button:hover {{
        transform: scale(1.02) !important; box-shadow: 0 0 20px rgba(0, 212, 170, 0.3) !important;
    }}
    
    /* Selection Cards */
    .game-card {{
        cursor: pointer; transition: all 0.3s ease;
        border: 1px solid {UI_COLORS['border']}; border-radius: 12px;
        padding: 16px; margin-bottom: 12px; background: {UI_COLORS['bg_secondary']};
    }}
    .game-card:hover {{ border-color: {UI_COLORS['accent']}; background: {UI_COLORS['bg_card']}; }}
    
    /* Odds Display */
    .odds-badge {{
        font-family: 'JetBrains+Mono', monospace; background: rgba(0, 212, 170, 0.1);
        color: {UI_COLORS['accent']}; padding: 4px 8px; border-radius: 6px; font-weight: bold;
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
            st.markdown(f"""
            <div style="background: {UI_COLORS['bg_card']}; border: 1px solid {UI_COLORS['border']}; border-radius: 16px; padding: 20px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="background: rgba(255,255,255,0.05); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; color: {UI_COLORS['text_secondary']};">{game.get('game_status_text', 'Scheduled')}</span>
                    <span style="font-family: 'JetBrains Mono'; font-size: 0.8rem; color: {UI_COLORS['accent']}; font-weight: bold;">{game['game_id'][-4:]}</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.1rem; font-weight: 800;">{game['away_team_abbr']}</span>
                        <span style="font-weight: bold; color: {UI_COLORS['text_secondary']};">@</span>
                        <span style="font-size: 1.1rem; font-weight: 800;">{game['home_team_abbr']}</span>
                    </div>
                    <div style="display: flex; justify-content: center; gap: 40px; margin-top: 5px;">
                        <span style="font-size: 0.8rem; color: {UI_COLORS['text_secondary']};">{game['away_team_city']}</span>
                        <span style="font-size: 0.8rem; color: {UI_COLORS['text_secondary']};">{game['home_team_city']}</span>
                    </div>
                </div>
                <div style="margin-top: 15px; display: flex; justify-content: center;"></div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Analyze {game['away_team_abbr']} @ {game['home_team_abbr']}", key=f"btn_{game['game_id']}", use_container_width=True):
                st.session_state.selected_game_id = game['game_id']
                st.session_state.active_tab = "🔬 Matchup Deep Dive"
                st.toast(f"Matchup {game['away_team_abbr']} @ {game['home_team_abbr']} selected!", icon="📊")
                st.rerun()

def main():
    inject_custom_css()
    
    st.title("🏀 NBA Parlay Generator")
    risk_pref, parlay_legs, api_key, use_demo, game_date = render_sidebar()
    
    # Custom Navigation
    tabs = ["📊 Today's Games", "🔬 Matchup Deep Dive", "🎯 Parlay Generator"]
    
    # We use a segmented control for a premium feel and programmatic switching
    selected_tab = st.segmented_control(
        "Navigation", 
        options=tabs, 
        selection_mode="single", 
        default=st.session_state.active_tab,
        key="nav_bar",
        label_visibility="collapsed"
    )
    
    # Sync segmented control back to session state if it changed manually
    if selected_tab and selected_tab != st.session_state.active_tab:
        st.session_state.active_tab = selected_tab

    st.divider()

    if st.session_state.active_tab == "📊 Today's Games":
        render_todays_games()
        
    elif st.session_state.active_tab == "🔬 Matchup Deep Dive":
        if st.session_state.selected_game_id and st.session_state.selected_game_id in st.session_state.game_analyses:
            render_matchup_deep_dive(
                st.session_state.selected_game_id, 
                st.session_state.all_bets_by_game, 
                st.session_state.game_analyses
            )
        else:
            st.info("Select 'Analyze Matchup' from the Today's Games tab to view deep dive stats.")

    elif st.session_state.active_tab == "🎯 Parlay Generator":
        st.header("Recommended Parlays")
        if not st.session_state.all_bets_by_game:
            st.info("Please fetch data first.")
        else:
            # Enforce 4-8 leg config
            from config import PARLAY_CONFIG
            PARLAY_CONFIG['min_legs'] = parlay_legs
            PARLAY_CONFIG['max_legs'] = parlay_legs
            
            parlays = generate_parlays(st.session_state.all_bets_by_game, risk_preference=risk_pref)
            
            if not parlays:
                st.warning(f"No {parlay_legs}-leg parlay combinations found matching the strict '{risk_pref}' risk requirements.", icon="⚠️")
            else:
                for idx, p in enumerate(parlays):
                    formatted = format_parlay_for_display(p, rank=idx+1)
                    
                    st.markdown(f"""
                    <div class="glass-card" style="padding: 0px; overflow: hidden; border-top: 4px solid {formatted['risk_color']};">
                        <div style="background: rgba(255,255,255,0.02); padding: 20px; border-bottom: 1px solid {UI_COLORS['border']};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h2 style="margin: 0; color: {UI_COLORS['text_primary']};">{formatted['title']}</h2>
                                <span style="background: {formatted['risk_bg']}; color: {formatted['risk_color']}; padding: 6px 12px; border-radius: 8px; font-weight: 800; font-size: 0.8rem; letter-spacing: 0.1em;">{formatted['risk_emoji']} {formatted['risk_level'].upper()} RISK</span>
                            </div>
                            <div style="color: {UI_COLORS['text_secondary']}; font-size: 0.9rem; margin-top: 4px;">{formatted['subtitle']}</div>
                        </div>
                        
                        <div style="padding: 24px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 25px; gap: 15px;">
                                <div style="text-align: center; flex: 1;">
                                    <div style="color: {UI_COLORS['text_secondary']}; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 5px;">Combined Odds</div>
                                    <div style="font-family: 'JetBrains Mono'; font-size: 1.4rem; font-weight: 800; color: {UI_COLORS['accent']};">{formatted['combined_odds']}</div>
                                </div>
                                <div style="text-align: center; flex: 1;">
                                    <div style="color: {UI_COLORS['text_secondary']}; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 5px;">Hit Probability</div>
                                    <div style="font-family: 'JetBrains Mono'; font-size: 1.4rem; font-weight: 800;">{formatted['probability']*100:.1f}%</div>
                                </div>
                                <div style="text-align: center; flex: 1;">
                                    <div style="color: {UI_COLORS['text_secondary']}; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 5px;">EV (+)</div>
                                    <div style="font-family: 'JetBrains Mono'; font-size: 1.4rem; font-weight: 800; color: #00D4AA;">{formatted['expected_value']:.2f}</div>
                                </div>
                            </div>
                            
                            <div style="background: rgba(0,0,0,0.2); border-radius: 12px; padding: 15px; margin-bottom: 25px; border: 1px dashed {UI_COLORS['border']};">
                                <span style="color: {UI_COLORS['text_secondary']}; font-size: 0.85rem; font-style: italic;">{formatted['description']}</span>
                            </div>

                            <h4 style="margin-bottom: 15px; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em; color: {UI_COLORS['text_secondary']};">Ticket Legs</h4>
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                    """, unsafe_allow_html=True)
                    
                    for leg in formatted["legs"]:
                        st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.03); border: 1px solid {UI_COLORS['border']}; padding: 12px 16px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: 700; font-size: 1rem;"><span style="margin-right: 8px;">{leg.get('bet_icon', '🏀')}</span> {leg['bet_label']}</div>
                                <div style="font-size: 0.8rem; color: {UI_COLORS['text_secondary']}; margin-top: 2px;">{leg['explanation']}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-family: 'JetBrains Mono'; font-size: 0.9rem; font-weight: bold; color: {UI_COLORS['accent']};">{leg['probability']*100:.0f}%</div>
                                <div style="font-size: 0.7rem; color: {UI_COLORS['text_secondary']};">PROB</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("</div></div><br/>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
