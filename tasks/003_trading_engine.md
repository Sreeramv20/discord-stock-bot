# Task 003 --- Trading Engine

Implement a full trading engine.

Commands:

/buy TICKER SHARES /sell TICKER SHARES

## Rules

User must have enough cash to buy.

User must own enough shares to sell.

Trades execute instantly at current price.

## Database Updates

Buying:

Decrease cash balance Increase portfolio shares Add transaction entry

Selling:

Increase cash balance Decrease shares Add transaction entry

## Edge Cases

Prevent:

Negative share amounts Zero share trades Invalid tickers

## Response Message

Example:

You bought 10 AAPL at \$185.23 Remaining Cash: \$48,147.70
