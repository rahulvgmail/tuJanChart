"""Touch and Hold/Reverse signal logic.

Replicates the spreadsheet formulas:
- Touch: AND(today_low < DMA, today_high > DMA)
- Signal: IF(touch, IF(price >= DMA, "Hold", "Reverse"), NULL)
"""


def compute_touch_and_signal(
    current_price: float,
    today_high: float,
    today_low: float,
    ma_value: float | None,
) -> tuple[bool, str | None]:
    """Compute touch detection and Hold/Reverse signal for a moving average.

    Args:
        current_price: Current close/last price.
        today_high: Today's high price.
        today_low: Today's low price.
        ma_value: The moving average value. None if insufficient data.

    Returns:
        (touch, signal) where:
        - touch: True if price range straddles the MA
        - signal: "Hold" if touching and price >= MA, "Reverse" if touching
          and price < MA, None if no touch
    """
    if ma_value is None or today_high is None or today_low is None:
        return False, None

    touch = today_low < ma_value and today_high > ma_value

    if not touch:
        return False, None

    signal = "Hold" if current_price >= ma_value else "Reverse"
    return True, signal
