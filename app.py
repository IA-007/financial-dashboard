import streamlit as st
import datetime
import math
import plotly.graph_objects as go
from data_handler import get_historical_data, get_company_info, prepare_seasonality_data, ASSET_CLASSES
from ml_forecaster import add_technical_indicators, generate_prophet_forecast

# Setup UI page config FIRST
st.set_page_config(page_title="AI Market Forecaster", layout="wide", page_icon="📈")

import streamlit_authenticator as stauth

# --- AUTHENTICATION ---
# Convert st.secrets to standard Python dictionaries
credentials = {"usernames": dict(st.secrets["credentials"]["usernames"])}

authenticator = stauth.Authenticate(
    credentials,
    st.secrets["cookie"]["name"],
    st.secrets["cookie"]["key"],
    st.secrets["cookie"]["expiry_days"],
    st.secrets.get("preauthorized", {"emails": []})
)

authenticator.login()

if st.session_state.get("authentication_status") is False:
    st.error('Username/password is incorrect')
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning('Please enter your username and password')
    st.stop()

# --- AUTHENTICATED AREA ---
authenticator.logout('Logout', 'sidebar')
st.sidebar.write(f"Welcome, *{st.session_state.get('name', 'Admin')}*!")
st.sidebar.markdown("---")

# ---------- SIDEBAR FILTERS ----------
st.sidebar.title("🛠️ Configuration")

# 1. Market & Asset Selection
market_choice = st.sidebar.selectbox("Market Category", list(ASSET_CLASSES.keys()))
asset_choice = st.sidebar.selectbox("Select Asset", ASSET_CLASSES[market_choice])

# 2. Historical Data Period
st.sidebar.subheader("History Period")
period_choice = st.sidebar.radio(
    "Data Depth", 
    ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"], 
    index=4, # default 2y
    horizontal=True
)

# 3. Technical Indicators Toggles
st.sidebar.subheader("Technical Indicators & Views")
layout_theme = st.sidebar.radio("Layout Theme", ["Classic", "Modern"], index=1, horizontal=True)
show_sma = st.sidebar.checkbox("Show SMA (20/50)", value=True)
show_rsi = st.sidebar.checkbox("Show RSI (14)", value=False)
show_macd = st.sidebar.checkbox("Show MACD", value=False)
show_momentum = st.sidebar.checkbox("Show Momentum (10d)", value=False)
show_bbands = st.sidebar.checkbox("Show Bollinger Bands", value=False)
show_seasonality = st.sidebar.checkbox("Show Seasonality (5 Yr)", value=False)

# 4. Machine Learning Forecast Toggles
st.sidebar.subheader("AI Prediction (Prophet)")
enable_ml = st.sidebar.checkbox("Enable ML Forecast", value=False)
if enable_ml:
    forecast_horizon = st.sidebar.slider("Forecast Horizon (Days)", min_value=7, max_value=180, value=30, step=7)
    show_ml_metrics = st.sidebar.checkbox("Show ML Risk/Reward Gauges", value=True)
else:
    forecast_horizon = 0
    show_ml_metrics = False

# ---------- MAIN DASHBOARD ----------
st.title(f"📈 Dashboard Previsionale: {asset_choice}")

# Fetch data using a caching function to speed up re-renders inside Streamlit
@st.cache_data(ttl=3600)
def load_data(ticker, period):
    df = get_historical_data(ticker, period)
    if not df.empty:
        # Add basic indicators mathematically
        df_ind = add_technical_indicators(df)
        return df_ind
    return df

@st.cache_data(ttl=86400)
def load_info(ticker):
    return get_company_info(ticker)

# Load data based on current selections
with st.spinner(f"Loading market data for {asset_choice}..."):
    df_main = load_data(asset_choice, period_choice)
    info = load_info(asset_choice)

if df_main.empty:
    st.error(f"Failed to fetch historical data for {asset_choice}. Please try another asset or period.")
else:
    # Top Information Metrics
    col1, col2, col3, col4 = st.columns(4)
    current_price = df_main['Close'].iloc[-1]
    prev_price = df_main['Close'].iloc[-2]
    price_change = current_price - prev_price
    pct_change = (price_change / prev_price) * 100
    
    col1.metric("Current Price", f"{current_price:.2f}", f"{pct_change:.2f}%")
    
    # Try to extract company/asset name from yfinance info
    asset_name = info.get("longName", info.get("shortName", asset_choice))
    st.markdown(f"**Asset:** {asset_name} | **Market:** {market_choice}")
    
    # --- PLOTLY CHARTING LOGIC ---
    # Create a base Candlestick chart
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=df_main['Date'],
        open=df_main['Open'],
        high=df_main['High'],
        low=df_main['Low'],
        close=df_main['Close'],
        name="Historical Price"
    ))
    
    # Add Technical Indicators overlay
    if show_sma and 'SMA_20' in df_main.columns:
        fig.add_trace(go.Scatter(x=df_main['Date'], y=df_main['SMA_20'], mode='lines', line=dict(color='orange', width=1.5), name='SMA 20'))
        fig.add_trace(go.Scatter(x=df_main['Date'], y=df_main['SMA_50'], mode='lines', line=dict(color='blue', width=1.5), name='SMA 50'))

    if show_bbands and 'BB_Upper' in df_main.columns:
        fig.add_trace(go.Scatter(x=df_main['Date'], y=df_main['BB_Upper'], line=dict(color='rgba(250,250,250,0.5)', dash='dash'), name='BB Upper'))
        fig.add_trace(go.Scatter(x=df_main['Date'], y=df_main['BB_Lower'], line=dict(color='rgba(250,250,250,0.5)', dash='dash'), fill='tonexty', fillcolor='rgba(250,250,250,0.1)', name='BB Lower'))

    # Add AI Prophet Forecast if enabled
    if enable_ml and len(df_main) > 50:
        with st.spinner(f"Running Meta Prophet ML Model for {forecast_horizon} days forecast..."):
             # We only pass data up to today to generate future projections
             df_forecast_result = generate_prophet_forecast(df_main, forecast_horizon)
             
             if not df_forecast_result.empty:
                  # Ensure timezone alignment for plotting (yfinance gives tz-naive now, prophet gives tz-naive)
                  # The future predicted dates are everything strictly after our last historical date
                  last_hist_date = df_main['Date'].iloc[-1]
                  last_hist_price = df_main['Close'].iloc[-1]
                  future_only = df_forecast_result[df_forecast_result['ds'] > last_hist_date]
                  
                  # Anchor lists to plot to avoid the visual "jump" gap
                  plot_dates = [last_hist_date] + future_only['ds'].tolist()
                  plot_yhat = [last_hist_price] + future_only['yhat'].tolist()
                  plot_upper = [last_hist_price] + future_only['yhat_upper'].tolist()
                  plot_lower = [last_hist_price] + future_only['yhat_lower'].tolist()
                  
                  # Plot Predicted Mean Line
                  fig.add_trace(go.Scatter(
                      x=plot_dates, 
                      y=plot_yhat, 
                      mode='lines', 
                      line=dict(color='fuchsia', width=2, dash='dot'),
                      name=f'Prophet ML Forecast ({forecast_horizon}d)'
                  ))
                  
                  # Plot Confidence Interval (Upper & Lower Bounds) as a shaded area
                  fig.add_trace(go.Scatter(
                      x=plot_dates + plot_dates[::-1],
                      y=plot_upper + plot_lower[::-1],
                      fill='toself',
                      fillcolor='rgba(255, 0, 255, 0.1)',
                      line=dict(color='rgba(255, 255, 255, 0)'),
                      name='95% Confidence Interval',
                      hoverinfo='skip'
                  ))
                  
                  st.success("🤖 ML Forecast generated successfully!")
                  
                  if show_ml_metrics:
                      # Probability of Rise Calculation
                      final_yhat = future_only['yhat'].iloc[-1]
                      final_lower = future_only['yhat_lower'].iloc[-1]
                      final_upper = future_only['yhat_upper'].iloc[-1]
                      sigma = (final_upper - final_lower) / 3.92
                      
                      if sigma > 0:
                          z_score = (last_hist_price - final_yhat) / (sigma * math.sqrt(2))
                          prob_up = (1.0 - (0.5 * (1 + math.erf(z_score)))) * 100
                      else:
                          prob_up = 100 if final_yhat > last_hist_price else 0
                          
                      # Max Drawdown Calculation
                      min_predicted_price = future_only['yhat_lower'].min()
                      if min_predicted_price < last_hist_price:
                          max_dd_pct = ((last_hist_price - min_predicted_price) / last_hist_price) * 100
                      else:
                          max_dd_pct = 0
                          
                      st.subheader(f"📊 ML Risk/Reward Metrics ({forecast_horizon} Days)")
                      g1, g2 = st.columns(2)
                      
                      fig_gauge_prob = go.Figure(go.Indicator(
                          mode = "gauge+number",
                          value = prob_up,
                          number = {'suffix': "%", 'valueformat': ".1f"},
                          title = {'text': "Probabilità di Rialzo", 'font': {'size': 18}},
                          gauge = {
                              'axis': {'range': [0, 100]},
                              'bar': {'color': "lightgreen" if prob_up >= 50 else "salmon"},
                              'steps': [
                                  {'range': [0, 40], 'color': "rgba(255, 0, 0, 0.2)"},
                                  {'range': [40, 60], 'color': "rgba(255, 255, 0, 0.2)"},
                                  {'range': [60, 100], 'color': "rgba(0, 255, 0, 0.2)"}],
                          }
                      ))
                      fig_gauge_prob.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
                      
                      fig_gauge_dd = go.Figure(go.Indicator(
                          mode = "gauge+number",
                          value = max_dd_pct,
                          number = {'suffix': "%", 'valueformat': ".1f"},
                          title = {'text': "Max Drawdown Previsto", 'font': {'size': 18}},
                          gauge = {
                              'axis': {'range': [0, max(30, max_dd_pct + 10)]},
                              'bar': {'color': "red"},
                              'steps': [
                                  {'range': [0, 10], 'color': "rgba(0, 255, 0, 0.2)"},
                                  {'range': [10, 20], 'color': "rgba(255, 255, 0, 0.2)"},
                                  {'range': [20, 100], 'color': "rgba(255, 0, 0, 0.2)"}],
                          }
                      ))
                      fig_gauge_dd.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
                      
                      g1.plotly_chart(fig_gauge_prob, use_container_width=True)
                      g2.plotly_chart(fig_gauge_dd, use_container_width=True)

             else:
                  st.warning("Forecasting failed due to insufficient valid data points.")
                  
    # Chart Styling
    fig.update_layout(
        title=f"Price History & ML Projection for {asset_choice}",
        yaxis_title="Price",
        xaxis_title="Date",
        template="plotly_dark",
        height=650,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis_rangeslider_visible=False # Turn off the default plotly rangeslider below candlestick
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # --- ADDITIONAL INDICATOR CHARTS ---
    active_sub_charts = []

    if show_rsi and 'RSI_14' in df_main.columns:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df_main['Date'], y=df_main['RSI_14'], line=dict(color='cyan'), name='RSI'))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought > 70")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold < 30")
        fig_rsi.update_layout(title="RSI (14 Days)", height=250, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        active_sub_charts.append(fig_rsi)

    if show_macd and 'MACD' in df_main.columns:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Bar(x=df_main['Date'], y=df_main['MACD'] - df_main['MACD_Signal'], name='Histogram', marker_color='gray'))
        fig_macd.add_trace(go.Scatter(x=df_main['Date'], y=df_main['MACD'], line=dict(color='yellow'), name='MACD'))
        fig_macd.add_trace(go.Scatter(x=df_main['Date'], y=df_main['MACD_Signal'], line=dict(color='orange'), name='Signal'))
        fig_macd.update_layout(title="MACD (12, 26, 9)", height=250, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        active_sub_charts.append(fig_macd)

    if show_momentum and 'Momentum' in df_main.columns:
        fig_mom = go.Figure()
        fig_mom.add_trace(go.Scatter(x=df_main['Date'], y=df_main['Momentum'], line=dict(color='magenta'), name='Momentum'))
        fig_mom.add_hline(y=0, line_dash="dash", line_color="white")
        fig_mom.update_layout(title="Momentum (10 Days)", height=250, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        active_sub_charts.append(fig_mom)

    if layout_theme == "Modern" and active_sub_charts:
        # Display side-by-side using columns
        cols = st.columns(len(active_sub_charts))
        for i, chart in enumerate(active_sub_charts):
            cols[i].plotly_chart(chart, use_container_width=True)
    elif layout_theme == "Classic" and active_sub_charts:
        # Display stacked
        for chart in active_sub_charts:
            st.plotly_chart(chart, use_container_width=True)

    # --- SEASONALITY (YoY) CHART ---
    if show_seasonality:
        st.subheader("🗓️ 5-Year Seasonality (Year-over-Year)")
        with st.spinner("Preparing seasonality data..."):
             # Fast path: If the user chose 5y, 10y, or max, we already have enough data in df_main
             if period_choice in ["5y", "10y", "max"]:
                  df_season = prepare_seasonality_data(df_main, years=5)
             else:
                  # Need to load 5 years of data specifically for this view
                  df_5y = load_data(asset_choice, "5y")
                  df_season = prepare_seasonality_data(df_5y, years=5)
             
             if not df_season.empty:
                  fig_season = go.Figure()
                  
                  # Plot a line for each year
                  years_present = df_season['Year'].unique()
                  
                  # Define a color palette for up to 6 years
                  colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
                  
                  for i, yr in enumerate(sorted(years_present)):
                       df_year = df_season[df_season['Year'] == yr]
                       # Thicker line for the current/latest year to make it stand out
                       line_width = 3 if yr == max(years_present) else 1.5
                       c = colors[i % len(colors)]
                       
                       fig_season.add_trace(go.Scatter(
                           x=df_year['Fake_Date'],
                           y=df_year['Close'],
                           mode='lines',
                           line=dict(width=line_width, color=c),
                           name=str(yr)
                       ))
                       
                  # --- Seasonality ML Projection for Current Year ---
                  current_year = datetime.datetime.now().year
                  if enable_ml and current_year in years_present and len(df_main) > 50:
                       # We project from today to Dec 31st of the current year
                       days_to_end_of_year = (datetime.datetime(current_year, 12, 31) - datetime.datetime.now()).days
                       if days_to_end_of_year > 0:
                           season_forecast = generate_prophet_forecast(df_main, days_to_end_of_year)
                           if not season_forecast.empty:
                               last_hist_date = df_main['Date'].iloc[-1]
                               future_season = season_forecast[season_forecast['ds'] > last_hist_date].copy()
                               
                               def map_to_2024(d):
                                   try:
                                        return d.replace(year=2024)
                                   except ValueError:
                                        return d
                               future_season['Fake_Date'] = future_season['ds'].apply(map_to_2024)
                               
                               fig_season.add_trace(go.Scatter(
                                   x=future_season['Fake_Date'],
                                   y=future_season['yhat'],
                                   mode='lines',
                                   line=dict(width=3, color='fuchsia', dash='dot'),
                                   name=f'{current_year} Forecast'
                               ))
                       
                  fig_season.update_layout(
                      template="plotly_dark",
                      height=500,
                      margin=dict(l=0, r=0, t=40, b=0),
                      xaxis=dict(
                          title="Month",
                          tickformat="%b" # Shows Jan, Feb, Mar, etc.
                      ),
                      yaxis_title="Price",
                      hovermode='x unified'
                  )
                  
                  st.plotly_chart(fig_season, use_container_width=True)
             else:
                  st.warning("Not enough data to compute 5-year seasonality.")

    # Raw Data Expander
    with st.expander("View Raw Historical Data (tail)"):
        st.dataframe(df_main.tail(20).sort_values(by='Date', ascending=False))
