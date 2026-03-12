# Task 002 --- Stock Market Data System

Implement a module that fetches real stock data.

## Library

Use yfinance.

## Features

Price lookup command:

/price TICKER

Example: /price AAPL

Bot response should include:

Ticker Company Name Current Price Day Change Percent Change Market Cap

## Additional Functions

create function:

get_stock_price(ticker)

Returns:

{ price: float, change: float, percent_change: float }

## Error Handling

Handle:

Invalid ticker API failure Network errors

## Optimization

Cache prices for 30 seconds to reduce API calls.
