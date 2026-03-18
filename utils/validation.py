import re

TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")


def validate_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(f"Invalid ticker symbol: `{ticker}`. Use 1-5 uppercase letters.")
    return ticker


def validate_shares(shares: int) -> int:
    if not isinstance(shares, int) or shares <= 0:
        raise ValueError("Number of shares must be a positive integer.")
    if shares > 1_000_000:
        raise ValueError("Maximum order size is 1,000,000 shares.")
    return shares


def validate_price(price: float) -> float:
    if price <= 0:
        raise ValueError("Price must be a positive number.")
    if price > 1_000_000:
        raise ValueError("Price exceeds maximum allowed value.")
    return round(price, 2)


def validate_expiry_days(days: int) -> int:
    if days < 1:
        raise ValueError("Expiry must be at least 1 day.")
    if days > 90:
        raise ValueError("Expiry cannot exceed 90 days.")
    return days
