# 🏀 NBA Parlay Generator & Game Analysis

![NBA Analysis](https://img.shields.io/badge/NBA-Analysis-orange?style=for-the-badge&logo=nba)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Machine Learning](https://img.shields.io/badge/ML-XGBoost%20%7C%20Sklearn-blue?style=for-the-badge)

A professional-grade predictive analytics platform for NBA game outcomes and parlay optimization. This tool leverages machine learning models (XGBoost, Random Forest, Logistic Regression) trained on historical data and real-time statistics from the NBA API to provide high-probability betting insights.

## 🌟 Key Features

- **🔬 Matchup Deep Dive**: Detailed statistical breakdown of home and away teams, including offensive/defensive ratings, pace, and recent form.
- **🤖 ML-Powered Predictions**: Ensemble model (soft voting) optimized for log-loss, featuring isotonic calibration for accurate probability estimation.
- **🤕 Injury & Rest Impact**: Intelligent logic that adjusts predictions based on missing key players and back-to-back game fatigue.
- **🎯 Parlay Optimizer**: Automatically generates high-EV (Expected Value) parlay combinations based on risk preference (Ultra Safe, Low, Balanced).
- **📈 Real-time Odds**: Integration with The-Odds-API to pull live bookmaker lines and identify value bets.
- **✨ Premium UI**: Modern, glassmorphic Streamlit interface with dynamic visualizations and responsive design.

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) (Custom CSS & Components)
- **Data Engine**: [nba_api](https://github.com/swar/nba_api)
- **ML Pipeline**: [XGBoost](https://xgboost.readthedocs.io/), [Scikit-Learn](https://scikit-learn.org/)
- **Data Handling**: Pandas, NumPy
- **Serialization**: Joblib

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- [NBA API](https://github.com/swar/nba_api) installed

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/NBA-GAME-ANALYSIS.git
   cd NBA-GAME-ANALYSIS
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

Launch the Streamlit dashboard:
```bash
streamlit run app.py
```

### ML Pipeline (Optional)

To retrain the model or run a backtest:
1. Run the training pipeline:
   ```bash
   python ml_pipeline.py
   ```
2. Run the backtester to verify performance:
   ```bash
   python backtester.py
   ```

## 📂 Project Structure

```text
├── .streamlit/             # Streamlit configuration
├── app.py                  # Main application entry point
├── analytics_engine.py      # Core predictive logic & ML inference
├── betting_intelligence.py  # Value bet detection & betting logic
├── data_fetcher.py         # NBA API integration & caching
├── ml_pipeline.py          # Model training & feature engineering
├── parlay_engine.py        # Parlay generation algorithms
├── player_analysis.py       # Individual player impact metrics
├── team_analysis.py         # Team-level statistical analysis
├── ui_components.py        # Custom UI rendering logic
├── config.py               # Global constants & styling tokens
├── nba_model.joblib        # Pre-trained model payload
└── requirements.txt        # Project dependencies
```

## ⚠️ Disclaimer

This tool is for **informational and entertainment purposes only**. Sports betting involves significant risk. We do not guarantee profits, and users should bet responsibly. Always cross-reference with official injury reports and bookmaker lines.

---
*Developed with ❤️ for NBA enthusiasts and data scientists.*
