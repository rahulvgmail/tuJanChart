"""Built-in screener definitions mapped from the spreadsheet.

Each screener is a dict with:
  - name: Display name (from links/Copyoflinks sheets)
  - slug: URL-safe identifier
  - category: Grouping for UI sidebar
  - conditions: List of {field, operator, value} dicts (AND-combined)

These ~90 screeners replicate the FILTER formulas from the spreadsheet's
links and Copyoflinks sheets.
"""

BUILTIN_SCREENERS = [
    # ========== 52-Week High Strategies ==========
    {
        "name": "52W Closing High + Result within 7 Days",
        "slug": "52w-closing-high-result-7d",
        "category": "52w_high",
        "conditions": [
            {"field": "is_52w_closing_high", "operator": "is_true"},
            {"field": "result_within_7d", "operator": "is_true"},
        ],
    },
    {
        "name": "52W Closing High + Result Declared",
        "slug": "52w-closing-high-result-declared",
        "category": "52w_high",
        "conditions": [
            {"field": "is_52w_closing_high", "operator": "is_true"},
            {"field": "result_declared_10d", "operator": "is_true"},
        ],
    },
    {
        "name": "52W Closing High + Result within 15 Days",
        "slug": "52w-closing-high-result-15d",
        "category": "52w_high",
        "conditions": [
            {"field": "is_52w_closing_high", "operator": "is_true"},
            {"field": "result_within_15d", "operator": "is_true"},
        ],
    },
    {
        "name": "52W High Intraday Today",
        "slug": "52w-high-intraday-today",
        "category": "52w_high",
        "conditions": [
            {"field": "is_52w_high_intraday", "operator": "is_true"},
        ],
    },
    {
        "name": "52W Closing High Today",
        "slug": "52w-closing-high-today",
        "category": "52w_high",
        "conditions": [
            {"field": "is_52w_closing_high", "operator": "is_true"},
        ],
    },
    {
        "name": "Yesterday was 52W Closing High",
        "slug": "52w-high-yesterday",
        "category": "52w_high",
        "conditions": [
            {"field": "was_52w_high_yesterday", "operator": "is_true"},
        ],
    },

    # ========== DMA Strategies ==========
    {
        "name": "10 DMA Hold",
        "slug": "10-dma-hold",
        "category": "dma",
        "conditions": [
            {"field": "dma_10_touch", "operator": "is_true"},
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
        ],
    },
    {
        "name": "20 DMA Hold",
        "slug": "20-dma-hold",
        "category": "dma",
        "conditions": [
            {"field": "dma_20_touch", "operator": "is_true"},
            {"field": "dma_20_signal", "operator": "eq", "value": "Hold"},
        ],
    },
    {
        "name": "50 DMA Hold",
        "slug": "50-dma-hold",
        "category": "dma",
        "conditions": [
            {"field": "dma_50_touch", "operator": "is_true"},
            {"field": "dma_50_signal", "operator": "eq", "value": "Hold"},
        ],
    },
    {
        "name": "100 DMA Hold",
        "slug": "100-dma-hold",
        "category": "dma",
        "conditions": [
            {"field": "dma_100_touch", "operator": "is_true"},
            {"field": "dma_100_signal", "operator": "eq", "value": "Hold"},
        ],
    },
    {
        "name": "200 DMA Hold",
        "slug": "200-dma-hold",
        "category": "dma",
        "conditions": [
            {"field": "dma_200_touch", "operator": "is_true"},
            {"field": "dma_200_signal", "operator": "eq", "value": "Hold"},
        ],
    },
    {
        "name": "10 DMA Reverse",
        "slug": "10-dma-reverse",
        "category": "dma",
        "conditions": [
            {"field": "dma_10_touch", "operator": "is_true"},
            {"field": "dma_10_signal", "operator": "eq", "value": "Reverse"},
        ],
    },
    {
        "name": "20 DMA Reverse",
        "slug": "20-dma-reverse",
        "category": "dma",
        "conditions": [
            {"field": "dma_20_touch", "operator": "is_true"},
            {"field": "dma_20_signal", "operator": "eq", "value": "Reverse"},
        ],
    },
    {
        "name": "50 DMA Reverse",
        "slug": "50-dma-reverse",
        "category": "dma",
        "conditions": [
            {"field": "dma_50_touch", "operator": "is_true"},
            {"field": "dma_50_signal", "operator": "eq", "value": "Reverse"},
        ],
    },
    {
        "name": "100 DMA Reverse",
        "slug": "100-dma-reverse",
        "category": "dma",
        "conditions": [
            {"field": "dma_100_touch", "operator": "is_true"},
            {"field": "dma_100_signal", "operator": "eq", "value": "Reverse"},
        ],
    },
    {
        "name": "200 DMA Reverse",
        "slug": "200-dma-reverse",
        "category": "dma",
        "conditions": [
            {"field": "dma_200_touch", "operator": "is_true"},
            {"field": "dma_200_signal", "operator": "eq", "value": "Reverse"},
        ],
    },
    {
        "name": "Any DMA Touch (Hold or Reverse)",
        "slug": "any-dma-touch",
        "category": "dma",
        "conditions": [
            # At least one DMA touch — uses is_true on any
            {"field": "dma_10_touch", "operator": "is_true"},
        ],
    },

    # ========== DMA + Color Combinations ==========
    {
        "name": "10 DMA Touch - Orange & Yellow",
        "slug": "10-dma-orange-yellow",
        "category": "dma_color",
        "conditions": [
            {"field": "dma_10_touch", "operator": "is_true"},
            {"field": "color", "operator": "in", "value": ["Orange", "Yellow"]},
        ],
    },
    {
        "name": "20 DMA Touch - Orange & Yellow",
        "slug": "20-dma-orange-yellow",
        "category": "dma_color",
        "conditions": [
            {"field": "dma_20_touch", "operator": "is_true"},
            {"field": "color", "operator": "in", "value": ["Orange", "Yellow"]},
        ],
    },
    {
        "name": "10 DMA Touch - Pink (Portfolio)",
        "slug": "10-dma-pink",
        "category": "dma_color",
        "conditions": [
            {"field": "dma_10_touch", "operator": "is_true"},
            {"field": "color", "operator": "eq", "value": "Pink"},
        ],
    },
    {
        "name": "20 DMA Touch - Pink (Portfolio)",
        "slug": "20-dma-pink",
        "category": "dma_color",
        "conditions": [
            {"field": "dma_20_touch", "operator": "is_true"},
            {"field": "color", "operator": "eq", "value": "Pink"},
        ],
    },
    {
        "name": "50 DMA Touch - Pink (Portfolio)",
        "slug": "50-dma-pink",
        "category": "dma_color",
        "conditions": [
            {"field": "dma_50_touch", "operator": "is_true"},
            {"field": "color", "operator": "eq", "value": "Pink"},
        ],
    },

    # ========== DMA + Result Date ==========
    {
        "name": "10 DMA Hold + Result Declared",
        "slug": "10-dma-hold-result-declared",
        "category": "dma_result",
        "conditions": [
            {"field": "dma_10_touch", "operator": "is_true"},
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
            {"field": "result_declared_10d", "operator": "is_true"},
        ],
    },
    {
        "name": "10 DMA Hold + Result within 15 Days",
        "slug": "10-dma-hold-result-15d",
        "category": "dma_result",
        "conditions": [
            {"field": "dma_10_touch", "operator": "is_true"},
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
            {"field": "result_within_15d", "operator": "is_true"},
        ],
    },
    {
        "name": "50 DMA Hold + Result Declared",
        "slug": "50-dma-hold-result-declared",
        "category": "dma_result",
        "conditions": [
            {"field": "dma_50_touch", "operator": "is_true"},
            {"field": "dma_50_signal", "operator": "eq", "value": "Hold"},
            {"field": "result_declared_10d", "operator": "is_true"},
        ],
    },

    # ========== Volume Strategies ==========
    {
        "name": "Volume Breakout",
        "slug": "volume-breakout",
        "category": "volume",
        "conditions": [
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },
    {
        "name": "Volume Breakout + 52W Closing High",
        "slug": "volume-breakout-52w-high",
        "category": "volume",
        "conditions": [
            {"field": "is_volume_breakout", "operator": "is_true"},
            {"field": "is_52w_closing_high", "operator": "is_true"},
        ],
    },
    {
        "name": "Volume Breakout + Result Declared",
        "slug": "volume-breakout-result-declared",
        "category": "volume",
        "conditions": [
            {"field": "is_volume_breakout", "operator": "is_true"},
            {"field": "result_declared_10d", "operator": "is_true"},
        ],
    },
    {
        "name": "Volume > Avg 140d",
        "slug": "volume-gt-avg-140d",
        "category": "volume",
        "conditions": [
            {"field": "today_volume", "operator": "gt_field", "value": "avg_vol_140d"},
        ],
    },
    {
        "name": "High Volume + Orange/Yellow",
        "slug": "high-volume-orange-yellow",
        "category": "volume",
        "conditions": [
            {"field": "is_volume_breakout", "operator": "is_true"},
            {"field": "color", "operator": "in", "value": ["Orange", "Yellow"]},
        ],
    },

    # ========== Gap Strategies ==========
    {
        "name": "Gap Up Today",
        "slug": "gap-up-today",
        "category": "gap",
        "conditions": [
            {"field": "is_gap_up", "operator": "is_true"},
        ],
    },
    {
        "name": "Gap Down Today",
        "slug": "gap-down-today",
        "category": "gap",
        "conditions": [
            {"field": "is_gap_down", "operator": "is_true"},
        ],
    },
    {
        "name": "Gap Up + 52W High + Volume Breakout",
        "slug": "gap-up-52w-high-volume",
        "category": "gap",
        "conditions": [
            {"field": "is_gap_up", "operator": "is_true"},
            {"field": "is_52w_closing_high", "operator": "is_true"},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },
    {
        "name": "Gap Up + Result Declared",
        "slug": "gap-up-result-declared",
        "category": "gap",
        "conditions": [
            {"field": "is_gap_up", "operator": "is_true"},
            {"field": "result_declared_10d", "operator": "is_true"},
        ],
    },

    # ========== WMA Strategies ==========
    {
        "name": "5 WMA Touch",
        "slug": "5-wma-touch",
        "category": "wma",
        "conditions": [
            {"field": "wma_5_touch", "operator": "is_true"},
        ],
    },
    {
        "name": "10 WMA Touch",
        "slug": "10-wma-touch",
        "category": "wma",
        "conditions": [
            {"field": "wma_10_touch", "operator": "is_true"},
        ],
    },
    {
        "name": "20 WMA Touch",
        "slug": "20-wma-touch",
        "category": "wma",
        "conditions": [
            {"field": "wma_20_touch", "operator": "is_true"},
        ],
    },
    {
        "name": "10 WMA Hold - Orange & Yellow",
        "slug": "10-wma-hold-orange-yellow",
        "category": "wma",
        "conditions": [
            {"field": "wma_10_touch", "operator": "is_true"},
            {"field": "wma_10_signal", "operator": "eq", "value": "Hold"},
            {"field": "color", "operator": "in", "value": ["Orange", "Yellow"]},
        ],
    },
    {
        "name": "20 WMA Hold - Orange & Yellow",
        "slug": "20-wma-hold-orange-yellow",
        "category": "wma",
        "conditions": [
            {"field": "wma_20_touch", "operator": "is_true"},
            {"field": "wma_20_signal", "operator": "eq", "value": "Hold"},
            {"field": "color", "operator": "in", "value": ["Orange", "Yellow"]},
        ],
    },

    # ========== Result Date Strategies ==========
    {
        "name": "Result within 7 Days",
        "slug": "result-within-7d",
        "category": "result",
        "conditions": [
            {"field": "result_within_7d", "operator": "is_true"},
        ],
    },
    {
        "name": "Result within 10 Days",
        "slug": "result-within-10d",
        "category": "result",
        "conditions": [
            {"field": "result_within_10d", "operator": "is_true"},
        ],
    },
    {
        "name": "Result within 15 Days",
        "slug": "result-within-15d",
        "category": "result",
        "conditions": [
            {"field": "result_within_15d", "operator": "is_true"},
        ],
    },
    {
        "name": "Result Declared (last 10 days)",
        "slug": "result-declared-10d",
        "category": "result",
        "conditions": [
            {"field": "result_declared_10d", "operator": "is_true"},
        ],
    },
    {
        "name": "Result Declared + 52W High",
        "slug": "result-declared-52w-high",
        "category": "result",
        "conditions": [
            {"field": "result_declared_10d", "operator": "is_true"},
            {"field": "is_52w_closing_high", "operator": "is_true"},
        ],
    },
    {
        "name": "Result Declared + Volume Breakout",
        "slug": "result-declared-volume-breakout",
        "category": "result",
        "conditions": [
            {"field": "result_declared_10d", "operator": "is_true"},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },

    # ========== Color-Based Strategies ==========
    {
        "name": "Pink (Portfolio) Stocks",
        "slug": "pink-portfolio",
        "category": "color",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Pink"},
        ],
    },
    {
        "name": "Orange Stocks",
        "slug": "orange-stocks",
        "category": "color",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Orange"},
        ],
    },
    {
        "name": "Yellow Stocks",
        "slug": "yellow-stocks",
        "category": "color",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Yellow"},
        ],
    },
    {
        "name": "Blue (Good Results) Stocks",
        "slug": "blue-good-results",
        "category": "color",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Blue"},
        ],
    },
    {
        "name": "Green (Watchlist) Stocks",
        "slug": "green-watchlist",
        "category": "color",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Green"},
        ],
    },
    {
        "name": "Red (Bad Results) Stocks",
        "slug": "red-bad-results",
        "category": "color",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Red"},
        ],
    },

    # ========== Combined Buy Strategies ==========
    {
        "name": "10 DMA Hold + Orange + Result Declared + Volume Breakout",
        "slug": "10-dma-hold-orange-result-volume",
        "category": "buy_strategy",
        "conditions": [
            {"field": "dma_10_touch", "operator": "is_true"},
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
            {"field": "color", "operator": "eq", "value": "Orange"},
            {"field": "result_declared_10d", "operator": "is_true"},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },
    {
        "name": "52W High + Gap Up + Volume Breakout",
        "slug": "52w-high-gap-up-volume",
        "category": "buy_strategy",
        "conditions": [
            {"field": "is_52w_closing_high", "operator": "is_true"},
            {"field": "is_gap_up", "operator": "is_true"},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },
    {
        "name": "52W High + Result within 7 Days + Volume",
        "slug": "52w-high-result-7d-volume",
        "category": "buy_strategy",
        "conditions": [
            {"field": "is_52w_closing_high", "operator": "is_true"},
            {"field": "result_within_7d", "operator": "is_true"},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },
    {
        "name": "DMA Hold + Orange/Yellow + Result 15d",
        "slug": "dma-hold-orange-yellow-result-15d",
        "category": "buy_strategy",
        "conditions": [
            {"field": "dma_10_touch", "operator": "is_true"},
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
            {"field": "color", "operator": "in", "value": ["Orange", "Yellow"]},
            {"field": "result_within_15d", "operator": "is_true"},
        ],
    },
    {
        "name": "Result Declared + 52W High + Gap Up",
        "slug": "result-declared-52w-gap-up",
        "category": "buy_strategy",
        "conditions": [
            {"field": "result_declared_10d", "operator": "is_true"},
            {"field": "is_52w_closing_high", "operator": "is_true"},
            {"field": "is_gap_up", "operator": "is_true"},
        ],
    },
    {
        "name": "Result Declared + Circuit/Volume + Orange",
        "slug": "result-declared-volume-orange",
        "category": "buy_strategy",
        "conditions": [
            {"field": "result_declared_10d", "operator": "is_true"},
            {"field": "is_volume_breakout", "operator": "is_true"},
            {"field": "color", "operator": "eq", "value": "Orange"},
        ],
    },

    # ========== 90-Day Extremes ==========
    {
        "name": "90-Day High Today",
        "slug": "90d-high-today",
        "category": "extremes",
        "conditions": [
            {"field": "is_90d_high", "operator": "is_true"},
        ],
    },
    {
        "name": "90-Day Low Touch",
        "slug": "90d-low-touch",
        "category": "extremes",
        "conditions": [
            {"field": "is_90d_low_touch", "operator": "is_true"},
        ],
    },
    {
        "name": "90-Day Low Touch + Pink (Portfolio)",
        "slug": "90d-low-touch-pink",
        "category": "extremes",
        "conditions": [
            {"field": "is_90d_low_touch", "operator": "is_true"},
            {"field": "color", "operator": "eq", "value": "Pink"},
        ],
    },

    # ========== Breakout Strategies ==========
    {
        "name": "Biweekly Breakout",
        "slug": "biweekly-breakout",
        "category": "breakout",
        "conditions": [
            {"field": "is_biweek_bo", "operator": "is_true"},
        ],
    },
    {
        "name": "Weekly Breakout",
        "slug": "weekly-breakout",
        "category": "breakout",
        "conditions": [
            {"field": "is_week_bo", "operator": "is_true"},
        ],
    },
    {
        "name": "Biweekly Breakout + Volume",
        "slug": "biweekly-breakout-volume",
        "category": "breakout",
        "conditions": [
            {"field": "is_biweek_bo", "operator": "is_true"},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },

    # ========== Positive Momentum ==========
    {
        "name": "Price Up > 3%",
        "slug": "price-up-3pct",
        "category": "momentum",
        "conditions": [
            {"field": "pct_change", "operator": "gt", "value": 3.0},
        ],
    },
    {
        "name": "Price Down > 3%",
        "slug": "price-down-3pct",
        "category": "momentum",
        "conditions": [
            {"field": "pct_change", "operator": "lt", "value": -3.0},
        ],
    },
    {
        "name": "Price Up > 5%",
        "slug": "price-up-5pct",
        "category": "momentum",
        "conditions": [
            {"field": "pct_change", "operator": "gt", "value": 5.0},
        ],
    },
    {
        "name": "Price Up > 5% + Volume Breakout",
        "slug": "price-up-5pct-volume",
        "category": "momentum",
        "conditions": [
            {"field": "pct_change", "operator": "gt", "value": 5.0},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },

    # ========== Multi-DMA Combinations ==========
    {
        "name": "10 & 20 DMA Hold",
        "slug": "10-20-dma-hold",
        "category": "multi_dma",
        "conditions": [
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
            {"field": "dma_20_signal", "operator": "eq", "value": "Hold"},
        ],
    },
    {
        "name": "10 & 20 & 50 DMA Hold",
        "slug": "10-20-50-dma-hold",
        "category": "multi_dma",
        "conditions": [
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
            {"field": "dma_20_signal", "operator": "eq", "value": "Hold"},
            {"field": "dma_50_signal", "operator": "eq", "value": "Hold"},
        ],
    },
    {
        "name": "Price Above All DMAs",
        "slug": "price-above-all-dmas",
        "category": "multi_dma",
        "conditions": [
            {"field": "current_price", "operator": "gt_field", "value": "dma_10"},
            {"field": "current_price", "operator": "gt_field", "value": "dma_20"},
            {"field": "current_price", "operator": "gt_field", "value": "dma_50"},
            {"field": "current_price", "operator": "gt_field", "value": "dma_100"},
            {"field": "current_price", "operator": "gt_field", "value": "dma_200"},
        ],
    },
    {
        "name": "Price Below All DMAs",
        "slug": "price-below-all-dmas",
        "category": "multi_dma",
        "conditions": [
            {"field": "current_price", "operator": "lt_field", "value": "dma_10"},
            {"field": "current_price", "operator": "lt_field", "value": "dma_20"},
            {"field": "current_price", "operator": "lt_field", "value": "dma_50"},
            {"field": "current_price", "operator": "lt_field", "value": "dma_100"},
            {"field": "current_price", "operator": "lt_field", "value": "dma_200"},
        ],
    },

    # ========== Portfolio Monitoring ==========
    {
        "name": "Pink + 10 DMA Hold + Volume",
        "slug": "pink-10-dma-hold-volume",
        "category": "portfolio",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Pink"},
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },
    {
        "name": "Pink + 52W High",
        "slug": "pink-52w-high",
        "category": "portfolio",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Pink"},
            {"field": "is_52w_closing_high", "operator": "is_true"},
        ],
    },
    {
        "name": "Pink + 90D Low Touch (Warning)",
        "slug": "pink-90d-low-warning",
        "category": "portfolio",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Pink"},
            {"field": "is_90d_low_touch", "operator": "is_true"},
        ],
    },
    {
        "name": "Pink + Result within 7 Days",
        "slug": "pink-result-7d",
        "category": "portfolio",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Pink"},
            {"field": "result_within_7d", "operator": "is_true"},
        ],
    },

    # ========== Orange Post-Result ==========
    {
        "name": "Orange + Result Declared + 52W High",
        "slug": "orange-result-52w-high",
        "category": "post_result",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Orange"},
            {"field": "result_declared_10d", "operator": "is_true"},
            {"field": "is_52w_closing_high", "operator": "is_true"},
        ],
    },
    {
        "name": "Orange + Result Declared + Gap Up",
        "slug": "orange-result-gap-up",
        "category": "post_result",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Orange"},
            {"field": "result_declared_10d", "operator": "is_true"},
            {"field": "is_gap_up", "operator": "is_true"},
        ],
    },
    {
        "name": "Orange + Result Declared + Volume Breakout",
        "slug": "orange-result-volume-breakout",
        "category": "post_result",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Orange"},
            {"field": "result_declared_10d", "operator": "is_true"},
            {"field": "is_volume_breakout", "operator": "is_true"},
        ],
    },
    {
        "name": "Orange + 10 DMA Hold",
        "slug": "orange-10-dma-hold",
        "category": "post_result",
        "conditions": [
            {"field": "color", "operator": "eq", "value": "Orange"},
            {"field": "dma_10_signal", "operator": "eq", "value": "Hold"},
        ],
    },
]
