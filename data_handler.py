import yfinance as yf
import pandas as pd
import datetime

# Pre-defined mapping of common ticker symbols for the user's requested asset classes
ASSET_CLASSES = {
    "US Stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"],
    "EU Stocks": ["SIE.DE", "MC.PA", "ASML.AS", "SAP.DE", "ENI.MI", "ISP.MI", "UCG.MI"],
    "Cryptocurrencies": ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"],
    "Futures": ["ES=F", "NQ=F", "GC=F", "CL=F", "SI=F"] # S&P500, Nasdaq, Gold, Crude Oil, Silver
}

def get_historical_data(ticker_symbol: str, period: str = "5y") -> pd.DataFrame:
    """
    Fetches historical daily market data for a given ticker from Yahoo Finance.
    
    Args:
        ticker_symbol (str): The Yahoo Finance ticker symbol (e.g., 'AAPL', 'BTC-USD').
        period (str): The time period to fetch (e.g., '1y', '5y', 'max').
        
    Returns:
        pd.DataFrame: A pandas DataFrame containing Open, High, Low, Close, Volume data.
                      Returns empty DataFrame if downloading fails.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            print(f"Warning: No data found for ticker {ticker_symbol}")
            return df
            
        # Optional: Reset index to make Date a column instead of index, useful for Plotly/Prophet
        df = df.reset_index()
        
        # Ensure timezone unaware datetimes for prophet compatibility later
        if 'Date' in df.columns and pd.api.types.is_datetime64tz_dtype(df['Date']):
             df['Date'] = df['Date'].dt.tz_localize(None)

        return df
    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        return pd.DataFrame()

def get_company_info(ticker_symbol: str) -> dict:
    """Fetches high-level company info/metadata."""
    try:
         ticker = yf.Ticker(ticker_symbol)
         return ticker.info
    except Exception:
         return {}
