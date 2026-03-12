Implement random market events.

Examples: tech crash energy rally

Events affect price multipliers temporarily.

## Implementation Details

### Market Events System

1. **Event Types**:
   - Tech Crash: 30% price reduction for tech stocks (AAPL, MSFT, GOOGL, TSLA)
   - Energy Rally: 50% price increase for energy stocks (XOM, CVX, RDS-A, BP)
   - Market Boom: 30% price increase for all major stocks
   - Economic Uncertainty: 20% price increase for all stocks with increased volatility

2. **Event Mechanics**:
   - Events are randomly triggered every 1-5 minutes
   - Each event lasts for a predetermined duration (2-5 minutes)
   - Events affect specific stock categories or all stocks
   - Price multipliers are applied to current prices during events

3. **Integration Points**:
   - Market class needs to track active events and apply multipliers
   - Stock price updates must consider active event multipliers
   - Trading engine should use updated stock prices with event multipliers
   - User interface should display active events

4. **Database Considerations**:
   - No new database tables required
   - Events stored in memory within Market class
   - Event expiration handled through timestamp checks

5. **User Experience**:
   - Events displayed to users when triggered
   - Prices adjust automatically during events
   - Trading decisions affected by temporary market conditions
