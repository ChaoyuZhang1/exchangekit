# ExchangeKit — trading days & market holidays

Static site listing **trading days and market closure days** for 32 major stock
exchanges, 2025–2028, with `.ics` subscriptions and a free JSON API.

## Features

- 32 exchanges: NYSE, NASDAQ, SSE, HKEX, TSE, LSE, Xetra, Euronext, TSX, ASX,
  NSE, KRX, TWSE, SGX, B3, JSE, BIST, MOEX, TASE, IDX and more
- Trading-day counts by month/year + full closure-day tables
- `.ics` calendar per exchange/year (Google/Apple/Outlook)
- Static JSON API: `/api/v1/exchange/{CODE}/{YYYY}.json`
- Live "market open/closed" indicator per exchange timezone

## Data

Exchange rules from [pandas-market-calendars](https://github.com/rshefters/pandas_market_calendars);
holiday names joined from the HolidayKit open-holiday dataset.

## Build & deploy

```bash
pip install pandas_market_calendars
python build.py
npx wrangler pages deploy dist --project-name exchangekit --branch main
```

Production: https://exchangekit.pages.dev

Related sites:
- https://holidaykit.pages.dev — public holidays & long weekends
- https://workdaykit.pages.dev — business days calculator
