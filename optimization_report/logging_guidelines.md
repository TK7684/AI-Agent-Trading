
# Logging Best Practices Guide

## Replace Print Statements
Instead of:
    print(f"Processing {symbol} at {price}")

Use:
    logger.info("Processing symbol", symbol=symbol, price=price)

## Log Levels
- DEBUG: Detailed diagnostic information
- INFO: General information about system operation
- WARNING: Something unexpected, but system continuing
- ERROR: Error occurred, but system can continue
- CRITICAL: Serious error, system may not continue

## Structured Logging
logger.info(
    "Trade executed",
    symbol=symbol,
    side=side,
    quantity=quantity,
    price=price,
    trade_id=trade_id
)

## Performance Logging
start_time = time.time()
# ... operation ...
logger.info(
    "Operation completed",
    operation="technical_analysis",
    duration_ms=(time.time() - start_time) * 1000,
    data_points=len(df)
)

## Error Logging
try:
    # risky operation
    result = risky_function()
except Exception as e:
    logger.error(
        "Operation failed",
        operation=risky_function.__name__,
        error=str(e),
        exc_info=True
    )
    raise
