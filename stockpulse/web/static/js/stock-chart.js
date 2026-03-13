/**
 * Stock chart using lightweight-charts v4 (TradingView).
 * Expects a #price-chart container with data-symbol attribute.
 */
(function () {
    var container = document.getElementById("price-chart");
    if (!container) return;

    var symbol = container.dataset.symbol;
    if (!symbol) return;

    var chart = LightweightCharts.createChart(container, {
        height: 400,
        layout: {
            background: { type: "solid", color: "#ffffff" },
            textColor: "#333",
            fontFamily: "system-ui, sans-serif",
        },
        grid: {
            vertLines: { color: "#f0f0f0" },
            horzLines: { color: "#f0f0f0" },
        },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: "#e5e7eb" },
        timeScale: {
            borderColor: "#e5e7eb",
            timeVisible: false,
        },
    });

    var candleSeries = chart.addCandlestickSeries({
        upColor: "#16a34a",
        downColor: "#dc2626",
        borderDownColor: "#dc2626",
        borderUpColor: "#16a34a",
        wickDownColor: "#dc2626",
        wickUpColor: "#16a34a",
    });

    var volumeSeries = chart.addHistogramSeries({
        color: "#93c5fd",
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
    });

    chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
    });

    // Period selector
    var toolbar = document.getElementById("chart-toolbar");
    if (toolbar) {
        toolbar.addEventListener("click", function (e) {
            if (e.target.tagName === "BUTTON") {
                toolbar.querySelectorAll("button").forEach(function (b) {
                    b.classList.remove("contrast");
                    b.classList.add("outline");
                });
                e.target.classList.remove("outline");
                e.target.classList.add("contrast");
                loadData(e.target.dataset.period);
            }
        });
    }

    function loadData(period) {
        fetch("/stocks/" + symbol + "/prices.json?period=" + period)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var candles = [];
                var volumes = [];
                for (var i = 0; i < data.length; i++) {
                    var d = data[i];
                    if (d.open != null && d.close != null) {
                        candles.push({
                            time: d.time,
                            open: d.open,
                            high: d.high,
                            low: d.low,
                            close: d.close,
                        });
                    }
                    if (d.volume != null) {
                        volumes.push({
                            time: d.time,
                            value: d.volume,
                            color: d.close >= d.open ? "#bbf7d0" : "#fecaca",
                        });
                    }
                }
                candleSeries.setData(candles);
                volumeSeries.setData(volumes);
                chart.timeScale().fitContent();
            });
    }

    // Load default (1 year)
    loadData("365d");

    // Handle resize
    var resizeObserver = new ResizeObserver(function () {
        chart.applyOptions({ width: container.clientWidth });
    });
    resizeObserver.observe(container);
})();
