import yfinance as yf
import pandas as pd
import datetime

# Pre-defined mapping of common ticker symbols for the user's requested asset classes
ASSET_CLASSES = {
    "US Stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"],
    "EU Stocks": ["SIE.DE", "MC.PA", "ASML.AS", "SAP.DE", "ENI.MI", "ISP.MI", "UCG.MI"],
    "EU Futures & Indices": ["STXE=F", "FDXS=F", "^STOXX50E", "^GDAXI", "FTSEMIB.MI"],
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

def prepare_seasonality_data(df: pd.DataFrame, years: int = 5) -> pd.DataFrame:
    """
    Prepares data for Year-over-Year seasonality plotting.
    Filters the last `years` of data, extracts the year, and maps all dates
    to a single leap year (e.g., 2024) to align the X-axis by month and day.
    """
    if df.empty or 'Date' not in df.columns:
        return pd.DataFrame()
        
    # Ensure Date is datetime type
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])
        
    last_date = df['Date'].max()
    start_date = last_date - pd.DateOffset(years=years)
    
    # Filter for the last N years
    df_filtered = df[df['Date'] >= start_date].copy()
    
    if df_filtered.empty:
        return df_filtered
        
    # Extract the Year as a column for the legend
    df_filtered['Year'] = df_filtered['Date'].dt.year
    
    # Create a Fake_Date mapped to year 2024 (a leap year) to align X axis
    def map_to_2024(d):
        try:
             # Try mapping to 2024
             return d.replace(year=2024)
        except ValueError:
             # Handle Feb 29 for non-leap years - though replacing TO a leap year 
             # from a non-leap year shouldn't raise ValueError. 
             # It might if replacing FROM a leap year to a NON-leap year.
             pass
        return d
        
    df_filtered['Fake_Date'] = df_filtered['Date'].apply(map_to_2024)
    
    return df_filtered
