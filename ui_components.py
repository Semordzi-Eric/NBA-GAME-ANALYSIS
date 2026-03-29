import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config import UI_COLORS, TEAM_COLORS, RISK_DISPLAY

def render_team_trend_chart(home_log, away_log, home_abbr, away_abbr):
    """
    Renders a Plotly line chart comparing recent scoring trends for both teams.
    """
    if not home_log or not away_log:
        st.info("Insufficient recent game log data to render trend chart.")
        return

    home_color = TEAM_COLORS.get(home_abbr, {}).get("primary", UI_COLORS["accent"])
    away_color = TEAM_COLORS.get(away_abbr, {}).get("primary", UI_COLORS["accent_secondary"])

    fig = go.Figure()

    # Home team
    fig.add_trace(go.Scatter(
        y=home_log,
        mode='lines+markers',
        name=f'{home_abbr} Points',
        line=dict(color=home_color, width=3),
        marker=dict(size=8)
    ))

    # Away team
    fig.add_trace(go.Scatter(
        y=away_log,
        mode='lines+markers',
        name=f'{away_abbr} Points',
        line=dict(color=away_color, width=3),
        marker=dict(size=8)
    ))

    fig.update_layout(
        title="Recent Scoring Form (Last Games)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=UI_COLORS["text_primary"]),
        xaxis=dict(title="Recent Games (Oldest → Newest)", showgrid=False, zeroline=False),
        yaxis=dict(title="Points Scored", showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_player_impact_chart(players_list, team_abbr):
    """
    Renders a bar chart of top players by impact score for a team.
    """
    if not players_list:
        st.write("No player data available.")
        return

    df = pd.DataFrame(players_list).head(5)
    
    color = TEAM_COLORS.get(team_abbr, {}).get("primary", UI_COLORS["accent"])

    fig = px.bar(
        df, 
        x='player_name', 
        y='impact_score',
        title=f"Top 5 Player Impact Scores ({team_abbr})",
        labels={'player_name': 'Player', 'impact_score': 'Impact Score (0-100)'},
        color_discrete_sequence=[color]
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=UI_COLORS["text_primary"]),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_safe_bets_table(bets):
    """
    Renders a Streamlit dataframe or styled list of bets for a specific game.
    """
    if not bets:
        st.write("No sufficiently safe bets identified for this matchup.")
        return

    st.markdown("### 🔥 Identified Value Bets")
    
    for bet in bets:
        risk_info = RISK_DISPLAY.get(bet["risk_level"], RISK_DISPLAY["medium"])
        
        st.markdown(f"""
        <div style="background-color: {UI_COLORS['bg_secondary']}; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid {risk_info['color']};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong style="font-size: 1.1em;">{bet['bet_icon']} {bet['bet_label']}</strong>
                <span style="background-color: {risk_info['bg']}; color: {risk_info['color']}; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">{risk_info['label']}</span>
            </div>
            <div style="color: {UI_COLORS['text_secondary']}; font-size: 0.95em; margin-bottom: 8px;">
                {bet['explanation']}
            </div>
            <div style="display: flex; gap: 15px; font-size: 0.9em;">
                <span><strong>Implied Prob:</strong> {bet['probability']*100:.1f}%</span>
                <span><strong>Decimal Odds:</strong> {bet.get('decimal_odds', 'N/A')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_matchup_deep_dive(game_id, all_bets_by_game, game_analyses):
    """
    Master detail view for the selected matchup.
    """
    ga = game_analyses.get(game_id)
    if not ga:
        st.error("Game analysis data not found.")
        return

    game = ga["game"]
    home_abbr = game["home_team_abbr"]
    away_abbr = game["away_team_abbr"]
    
    st.header(f"Matchup Analysis: {away_abbr} @ {home_abbr}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### 🏠 {game['home_team_city']} {game['home_team_name']}")
        home_score = ga['home_analysis']['strength_score']
        st.metric("Team Strength Score", f"{home_score}/100")
        render_player_impact_chart(ga["home_players"], home_abbr)
        
    with col2:
        st.markdown(f"### ✈️ {game['away_team_city']} {game['away_team_name']}")
        away_score = ga['away_analysis']['strength_score']
        st.metric("Team Strength Score", f"{away_score}/100")
        render_player_impact_chart(ga["away_players"], away_abbr)
        
    st.divider()
    
    home_pts_history = ga['home_analysis']['recent_form'].get('point_trend', [])
    away_pts_history = ga['away_analysis']['recent_form'].get('point_trend', [])
    
    render_team_trend_chart(home_pts_history, away_pts_history, home_abbr, away_abbr)
    
    st.divider()
    bets = all_bets_by_game.get(game_id, [])
    render_safe_bets_table(bets)
