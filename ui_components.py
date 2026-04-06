import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config import UI_COLORS, TEAM_COLORS, RISK_DISPLAY
from analysis_fetcher import get_market_sentiment

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
                <span style="color: {'#00D4AA' if bet.get('expected_value', 0) > 0 else UI_COLORS['text_secondary']};">
                    <strong>Value (EV):</strong> {bet.get('expected_value', 0.0):+.2f}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_market_sentiment(home_abbr, away_abbr):
    """
    Renders public vs sharp betting splits.
    """
    home_s = get_market_sentiment(home_abbr)
    away_s = get_market_sentiment(away_abbr)
    
    st.markdown("### 📊 Market Sentiment & System Plays")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid {UI_COLORS['border']}; padding: 15px; border-radius: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <b>{home_abbr} Sentiment</b>
                <span style="color: {UI_COLORS['accent']}; font-weight: bold;">{home_s['sentiment']}</span>
            </div>
            <div style="font-size: 0.85rem; margin-bottom: 5px;">Public Bets: <b>{home_s['public_pct']}%</b></div>
            <div style="height: 6px; background: #333; border-radius: 3px; margin-bottom: 12px;">
                <div style="width: {home_s['public_pct']}%; height: 100%; background: {UI_COLORS['accent']}; border-radius: 3px;"></div>
            </div>
            <div style="font-size: 0.85rem; margin-bottom: 5px;">Sharp Money: <b>{home_s['money_pct']}%</b></div>
             <div style="height: 6px; background: #333; border-radius: 3px; margin-bottom: 15px;">
                <div style="width: {home_s['money_pct']}%; height: 100%; background: #00A383; border-radius: 3px;"></div>
            </div>
            <div style="font-size: 0.8rem; color: {UI_COLORS['text_secondary']}; font-style: italic;">{home_s['system_play']}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid {UI_COLORS['border']}; padding: 15px; border-radius: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <b>{away_abbr} Sentiment</b>
                <span style="color: {UI_COLORS['accent']}; font-weight: bold;">{away_s['sentiment']}</span>
            </div>
            <div style="font-size: 0.85rem; margin-bottom: 5px;">Public Bets: <b>{away_s['public_pct']}%</b></div>
            <div style="height: 6px; background: #333; border-radius: 3px; margin-bottom: 12px;">
                <div style="width: {away_s['public_pct']}%; height: 100%; background: {UI_COLORS['accent_secondary']}; border-radius: 3px;"></div>
            </div>
            <div style="font-size: 0.85rem; margin-bottom: 5px;">Sharp Money: <b>{away_s['money_pct']}%</b></div>
             <div style="height: 6px; background: #333; border-radius: 3px; margin-bottom: 15px;">
                <div style="width: {away_s['money_pct']}%; height: 100%; background: #4D79FF; border-radius: 3px;"></div>
            </div>
            <div style="font-size: 0.8rem; color: {UI_COLORS['text_secondary']}; font-style: italic;">{away_s['system_play']}</div>
        </div>
        """, unsafe_allow_html=True)


def render_win_probability_gauge(home_prob, home_abbr, away_abbr):
    """
    Renders a gauge chart for win probability.
    """
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = home_prob * 100,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"{home_abbr} Win Probability", 'font': {'size': 18, 'family': 'Outfit'}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': UI_COLORS['text_secondary']},
            'bar': {'color': TEAM_COLORS.get(home_abbr, {}).get("primary", UI_COLORS['accent'])},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': UI_COLORS['border'],
            'steps': [
                {'range': [0, 40], 'color': 'rgba(255, 0, 0, 0.1)'},
                {'range': [40, 60], 'color': 'rgba(255, 255, 0, 0.1)'},
                {'range': [60, 100], 'color': 'rgba(0, 255, 0, 0.1)'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': UI_COLORS['text_primary'], 'family': "Inter"},
        height=300,
        margin=dict(l=30, r=30, t=50, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_team_comparison_radar(home_ga, away_ga, home_abbr, away_abbr):
    """
    Renders a radar chart comparing teams across 5 dimensions.
    """
    categories = ['Offense', 'Defense', 'Pace', 'SOS', 'Recent Form']
    
    # Normalize values for radar (0-100)
    # home_ga['offensive_rating'] is ~115, away_ga['offensive_rating'] is ~112
    # defensive_rating is inverted
    
    h_off = (home_ga['offensive_rating'] - 100) * 4 # roughly 0-100 for 100-125
    a_off = (away_ga['offensive_rating'] - 100) * 4
    
    h_def = 100 - (home_ga['defensive_rating'] - 100) * 4
    a_def = 100 - (away_ga['defensive_rating'] - 100) * 4
    
    h_pace = home_ga['pace']
    a_pace = away_ga['pace']
    
    h_sos = home_ga['recent_form'].get('sos', 0.5) * 100
    a_sos = away_ga['recent_form'].get('sos', 0.5) * 100
    
    h_form = home_ga['recent_form']['win_rate'] * 100
    a_form = away_ga['recent_form']['win_rate'] * 100

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=[h_off, h_def, h_pace, h_sos, h_form],
        theta=categories,
        fill='toself',
        name=home_abbr,
        line=dict(color=TEAM_COLORS.get(home_abbr, {}).get("primary", UI_COLORS['accent']))
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=[a_off, a_def, a_pace, a_sos, a_form],
        theta=categories,
        fill='toself',
        name=away_abbr,
        line=dict(color=TEAM_COLORS.get(away_abbr, {}).get("primary", UI_COLORS['accent_secondary']))
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            bgcolor="rgba(0,0,0,0)"
        ),
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': UI_COLORS['text_primary'], 'family': "Inter"},
        height=400,
        margin=dict(l=80, r=80, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_injury_impact_news(ga):
    """
    Renders a concise summary of missing players and their team-wide impact.
    """
    home_missing = ga["prediction"].get("home_missing_players", [])
    away_missing = ga["prediction"].get("away_missing_players", [])
    
    if not home_missing and not away_missing:
        return

    st.markdown("### 📰 Availability & Model Impact")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if home_missing:
            st.markdown(f"""
            <div style="background: rgba(255, 75, 75, 0.1); border: 1px solid rgba(255, 75, 75, 0.3); padding: 15px; border-radius: 12px;">
                <b style="color: #FF4B4B;">🚨 {ga['game']['home_team_abbr']} Inactive:</b><br/>
                <span style="font-size: 0.9rem;">{', '.join(home_missing)}</span><br/>
                <div style="margin-top: 8px; font-size: 0.85rem; opacity: 0.8;">Model Penalty: <b>{-ga['prediction'].get('home_penalty', 0):.1f}</b> pts</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: rgba(0, 212, 170, 0.05); border: 1px solid rgba(0, 212, 170, 0.2); padding: 15px; border-radius: 12px; color: {UI_COLORS['accent']};">
                ✅ <b>{ga['game']['home_team_abbr']} Healthy</b>
            </div>
            """, unsafe_allow_html=True)
            
    with col2:
        if away_missing:
            st.markdown(f"""
            <div style="background: rgba(255, 75, 75, 0.1); border: 1px solid rgba(255, 75, 75, 0.3); padding: 15px; border-radius: 12px;">
                <b style="color: #FF4B4B;">🚨 {ga['game']['away_team_abbr']} Inactive:</b><br/>
                <span style="font-size: 0.9rem;">{', '.join(away_missing)}</span><br/>
                <div style="margin-top: 8px; font-size: 0.85rem; opacity: 0.8;">Model Penalty: <b>{-ga['prediction'].get('away_penalty', 0):.1f}</b> pts</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: rgba(0, 212, 170, 0.05); border: 1px solid rgba(0, 212, 170, 0.2); padding: 15px; border-radius: 12px; color: {UI_COLORS['accent']};">
                ✅ <b>{ga['game']['away_team_abbr']} Healthy</b>
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
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    # Summary Stats & Mismatches
    st.markdown("### 🎯 Analytics HUD")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Proj. Pace", ga["expected_total"].get("pace", 100))
    with col2: st.metric("Spread", f"{ga['prediction']['predicted_spread']:+.1f}")
    with col3: st.metric("Total", ga["expected_total"]["expected_total"])
    with col4: st.metric("Mismatch Score", f"{ga['prediction'].get('mismatch_score', 0):+.1f}")
    
    # Mismatch Reasons
    reasons = ga["prediction"].get("mismatch_reasons", [])
    if reasons:
        st.info("💡 **Model Note**: " + " • ".join(reasons))

    st.divider()

    # Efficiency Comparison
    st.markdown("### 🚀 Power Metrics (Per 100 Possessions)")
    
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.write(f"**{home_abbr} Efficiency**")
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); padding: 10px; border-left: 4px solid {UI_COLORS['accent']}; margin-bottom: 5px;">
            ORtg: <b>{ga['home_analysis']['offensive_rating']}</b> | DRtg: <b>{ga['home_analysis']['defensive_rating']}</b>
        </div>
        """, unsafe_allow_html=True)
        # Four Factors
        ff = ga['home_analysis']['recent_form']['four_factors']
        st.caption(f"eFG%: {ff['efg_pct']}% | TOV%: {ff['tov_pct']}% | ORB%: {ff['orb_pct']}% | FTR: {ff['ft_rate']}")

    with col_r:
        st.write(f"**{away_abbr} Efficiency**")
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); padding: 10px; border-left: 4px solid {UI_COLORS['accent_secondary']}; margin-bottom: 5px;">
            ORtg: <b>{ga['away_analysis']['offensive_rating']}</b> | DRtg: <b>{ga['away_analysis']['defensive_rating']}</b>
        </div>
        """, unsafe_allow_html=True)
        # Four Factors
        ff = ga['away_analysis']['recent_form']['four_factors']
        st.caption(f"eFG%: {ff['efg_pct']}% | TOV%: {ff['tov_pct']}% | ORB%: {ff['orb_pct']}% | FTR: {ff['ft_rate']}")

    st.divider()

    # Comparison Visualizations
    col_viz1, col_viz2 = st.columns([1, 1])
    
    with col_viz1:
        render_team_comparison_radar(ga['home_analysis'], ga['away_analysis'], home_abbr, away_abbr)
    
    with col_viz2:
        render_win_probability_gauge(ga['prediction']['home_win_prob'], home_abbr, away_abbr)
    st.markdown('</div>', unsafe_allow_html=True)

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
    
    # News & Impact
    render_injury_impact_news(ga)
    
    st.divider()
    
    # Market Sentiment
    render_market_sentiment(home_abbr, away_abbr)
    
    st.divider()
    
    home_pts_history = ga['home_analysis']['recent_form'].get('point_trend', [])
    away_pts_history = ga['away_analysis']['recent_form'].get('point_trend', [])
    
    render_team_trend_chart(home_pts_history, away_pts_history, home_abbr, away_abbr)
    
    st.divider()
    bets = all_bets_by_game.get(game_id, [])
    render_safe_bets_table(bets)
