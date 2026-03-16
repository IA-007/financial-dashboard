import streamlit as st
import datetime
import plotly.graph_objects as go
from data_handler import get_historical_data, get_company_info, ASSET_CLASSES
from ml_forecaster import add_technical_indicators, generate_prophet_forecast

# Setup UI page config FIRST
st.set_page_config(page_title="AI Market Forecaster", layout="wide", page_icon="📈")

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
st.sidebar.subheader("Technical Indicators")
show_sma = st.sidebar.checkbox("Show SMA (20/50)", value=True)
show_rsi = st.sidebar.checkbox("Show RSI (14)", value=False)

# 4. Machine Learning Forecast Toggles
st.sidebar.subheader("AI Prediction (Prophet)")
enable_ml = st.sidebar.checkbox("Enable ML Forecast", value=False)
if enable_ml:
    forecast_horizon = st.sidebar.slider("Forecast Horizon (Days)", min_value=7, max_value=180, value=30, step=7)
else:
    forecast_horizon = 0

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

    # Add AI Prophet Forecast if enabled
    if enable_ml and len(df_main) > 50:
        with st.spinner(f"Running Meta Prophet ML Model for {forecast_horizon} days forecast..."):
             # We only pass data up to today to generate future projections
             df_forecast_result = generate_prophet_forecast(df_main, forecast_horizon)
             
             if not df_forecast_result.empty:
                  # Ensure timezone alignment for plotting (yfinance gives tz-naive now, prophet gives tz-naive)
                  # The future predicted dates are everything strictly after our last historical date
                  last_hist_date = df_main['Date'].iloc[-1]
                  future_only = df_forecast_result[df_forecast_result['ds'] > last_hist_date]
                  
                  # Plot Predicted Mean Line
                  fig.add_trace(go.Scatter(
                      x=future_only['ds'], 
                      y=future_only['yhat'], 
                      mode='lines', 
                      line=dict(color='fuchsia', width=2, dash='dot'),
                      name=f'Prophet ML Forecast ({forecast_horizon}d)'
                  ))
                  
                  # Plot Confidence Interval (Upper & Lower Bounds) as a shaded area
                  fig.add_trace(go.Scatter(
                      x=future_only['ds'].tolist() + future_only['ds'].tolist()[::-1],
                      y=future_only['yhat_upper'].tolist() + future_only['yhat_lower'].tolist()[::-1],
                      fill='toself',
                      fillcolor='rgba(255, 0, 255, 0.1)',
                      line=dict(color='rgba(255, 255, 255, 0)'),
                      name='95% Confidence Interval',
                      hoverinfo='skip'
                  ))
                  
                  st.success("🤖 ML Forecast generated successfully!")
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
    
    # --- SEPARATE CHART FOR RSI ---
    if show_rsi and 'RSI_14' in df_main.columns:
        st.subheader("RSI (14 Days)")
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df_main['Date'], y=df_main['RSI_14'], line=dict(color='cyan'), name='RSI'))
        # Overbought / Oversold lines
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought > 70")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold < 30")
        
        fig_rsi.update_layout(height=300, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_rsi, use_container_width=True)

    # Raw Data Expander
    with st.expander("View Raw Historical Data (tail)"):
        st.dataframe(df_main.tail(20).sort_values(by='Date', ascending=False))
