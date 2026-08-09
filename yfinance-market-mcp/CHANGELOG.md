# Changelog

All notable changes to yfinance-market-mcp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2025-04-15

### Fixed
- Fixed `calculate_range` tool to correctly fetch Day's Range (dayLow/dayHigh) for options contracts
- Changed `_get_contract_day_range` function to use `ticker.info` instead of `ticker.history()` which was returning empty data for options contracts
- Now correctly retrieves `regularMarketDayLow`/`regularMarketDayHigh` and `dayLow`/`dayHigh` from contract info
- Resolves issue where `day_low_x100`, `day_high_x100`, and `pct` values were appearing as `null` in the response

### Technical Details
- The yfinance library provides day range data for options contracts through the `.info` property, not through historical data
- The function now properly falls back from `regularMarketDay*` fields to standard `day*` fields for compatibility

## [0.3.1] - Previous release

- Initial stable release with calculate_range functionality
