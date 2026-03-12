# Task 001 --- Full Project Architecture for Discord Paper Trading Bot

You are building a **feature-rich Discord paper trading bot** where
users can trade stocks with fake money.

## Core Requirements

Every user starts with **\$50,000 virtual cash**.

The bot should support:

-   Slash commands
-   Portfolio tracking
-   Leaderboards
-   Live stock prices
-   Transaction history
-   Daily performance tracking
-   Admin tools
-   Cooldowns and anti-spam protection

## Tech Stack

Python discord.py SQLite yfinance

## Required Project Structure

Create the following file structure:

discord-stock-bot/ bot.py config.py database.py trading.py market.py
commands/ portfolio.py trading_commands.py leaderboard.py
market_commands.py utils/ calculations.py formatting.py database.db

## Database Tables

users - user_id - username - cash_balance - created_at

portfolios - user_id - ticker - shares

transactions - id - user_id - ticker - type - shares - price - timestamp

## Deliverables

Generate working code that:

-   Initializes database automatically
-   Registers Discord slash commands
-   Handles new user creation with \$50k balance
