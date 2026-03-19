import pandas as pd
import numpy as np
from prophet import Prophet

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates basic technical indicators: Simple Moving Averages (20, 50) and RSI (14).
    Expects a DataFrame with a 'Close' column.
    """
    if df.empty or 'Close' not in df.columns:
        return df

    # Copy to avoid SettingWithCopyWarning
    df_calc = df.copy()

    # Moving Averages
    df_calc['SMA_20'] = df_calc['Close'].rolling(window=20).mean()
    df_calc['SMA_50'] = df_calc['Close'].rolling(window=50).mean()

    # Relative Strength Index (RSI) - 14 Days
    delta = df_calc['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
    # Handle division by zero
    rs = gain / loss.replace(0, np.nan)
    df_calc['RSI_14'] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema_12 = df_calc['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df_calc['Close'].ewm(span=26, adjust=False).mean()
    df_calc['MACD'] = ema_12 - ema_26
    df_calc['MACD_Signal'] = df_calc['MACD'].ewm(span=9, adjust=False).mean()

    # Momentum (10 days)
    df_calc['Momentum'] = df_calc['Close'].diff(periods=10)

    # Bollinger Bands
    df_calc['BB_Middle'] = df_calc['Close'].rolling(window=20).mean()
    std_20 = df_calc['Close'].rolling(window=20).std()
    df_calc['BB_Upper'] = df_calc['BB_Middle'] + (std_20 * 2)
    df_calc['BB_Lower'] = df_calc['BB_Middle'] - (std_20 * 2)

    return df_calc

def generate_prophet_forecast(df: pd.DataFrame, days_to_forecast: int = 30) -> pd.DataFrame:
    """
    Trains a Prophet ML model on historical 'Close' prices and predicts the future.
    Expects a DataFrame with 'Date' and 'Close' columns.
    
    Returns:
        pd.DataFrame: A dataframe with columns ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
        suitable for plotting the forecast and confidence intervals.
    """
    if df.empty or 'Date' not in df.columns or 'Close' not in df.columns:
         print("Validation failed: DataFrame missing required columns for Prophet.")
         return pd.DataFrame()
         
    if len(df) < 50:
         print("Warning: Insufficient data rows for reliable Prophet forecasting (<50).")
         return pd.DataFrame()

    try:
        # Prophet strictly requires columns named 'ds' (datestamp) and 'y' (target variable)
        df_prophet = df[['Date', 'Close']].rename(columns={'Date': 'ds', 'Close': 'y'})
        
        # Remove any rows with NaN in y to prevent fitting errors
        df_prophet = df_prophet.dropna(subset=['y'])

        # Initialize and fit model
        # daily_seasonality=True is useful for crypto. For stocks, it might be less relevant 
        # but Prophet handles it well automatically based on data density.
        model = Prophet(daily_seasonality=False, yearly_seasonality=True, weekly_seasonality=False)
        model.fit(df_prophet)

        # Create future dataframe for forecasting
        future = model.make_future_dataframe(periods=days_to_forecast)
        
        # Predict
        forecast = model.predict(future)
        
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    except Exception as e:
        print(f"Prophet forecasting failed: {e}")
        return pd.DataFrame()
