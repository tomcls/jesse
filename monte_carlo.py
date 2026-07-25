from jesse.enums import exchanges
import os

import jesse.helpers as jh
from jesse.research import get_candles
from jesse.research.monte_carlo import (
    monte_carlo_candles, 
    monte_carlo_trades,
    print_monte_carlo_candles_summary, 
    plot_monte_carlo_candles_chart,
    print_monte_carlo_trades_summary, 
    plot_monte_carlo_trades_chart
)
from jesse.research.monte_carlo.candle_pipelines import GaussianNoiseCandlesPipeline, MovingBlockBootstrapCandlesPipeline

# =============================================================================
# CONFIGURATION - MODIFY ALL SETTINGS HERE
# =============================================================================

# Trading Routes Configuration
TRADING_ROUTES = [
    {"exchange": exchanges.BINANCE_PERPETUAL_FUTURES, "symbol": "ETH-USDT", "timeframe": "30m", "strategy": "ETHBTCStatArb"},
    {"exchange": exchanges.BINANCE_PERPETUAL_FUTURES, "symbol": "ETC-USDT", "timeframe": "30m", "strategy": "ETHBTCStatArb"},
]


# Simulation Configuration
SIMULATION_CONFIG = {
    "num_scenarios": 40,  # Back to normal
    "start_date": "2021-01-01", 
    "end_date": "2025-11-09",
    "progress_bar": True,
    "benchmark": True,
    "fast_mode": True,
}

# Strategy Configuration
STRATEGY_CONFIG = {
    "starting_balance": 10_000,
    "fee": 0.05 / 100,
    "type": "futures",
    "futures_leverage": 10,
    "futures_leverage_mode": "cross",
    "warm_up_candles": 210,
}

# Monte Carlo Candles Pipeline Configuration
MONTE_CARLO_CANDLES_CONFIG = {
    # "pipeline_class": MovingBlockBootstrapCandlesPipeline,
    # "pipeline_kwargs": {"batch_size": 7 * 24 * 60}, # 1 week batches
    "pipeline_class": GaussianNoiseCandlesPipeline,
    "pipeline_kwargs": {"batch_size": 7 * 24 * 60, "close_sigma": 10.0, "high_sigma": 5.0, "low_sigma": 5.0}, # 1 week batches
}

# =============================================================================


def get_configured_routes():
    routes = []
    for route in TRADING_ROUTES:
        routes.append({
            'exchange': route['exchange'],
            'symbol': route['symbol'], 
            'timeframe': route['timeframe'],
            'strategy': route['strategy']
        })
    data_routes = []
    for route in DATA_ROUTES:
        data_routes.append({
            'exchange': route['exchange'],
            'symbol': route['symbol'],
            'timeframe': route['timeframe']
        })
    return routes, data_routes


def prepare_candles_for_simulations(routes: list, data_routes: list, start_date_str: str, finish_date_str: str, config: dict):
    all_routes = routes + data_routes
    trading_candles = {}
    warmup_candles = {}
    unique_symbol_exchanges = set()
    for route in all_routes:
        unique_symbol_exchanges.add((route["exchange"], route["symbol"], route["timeframe"]))
    for route_exchange, route_symbol, route_timeframe in unique_symbol_exchanges:
        _warmup_candles, _trading_candles = get_candles(
            route_exchange,
            route_symbol,
            route_timeframe,
            jh.date_to_timestamp(start_date_str),
            jh.date_to_timestamp(finish_date_str),
            config["warm_up_candles"],
            caching=True,
            is_for_jesse=True,
        )
        key = jh.key(route_exchange, route_symbol)
        if key not in trading_candles:
            trading_candles[key] = {
                "exchange": route_exchange,
                "symbol": route_symbol,
                "candles": _trading_candles,
                "timeframe": route_timeframe,
            }
            warmup_candles[key] = {
                "exchange": route_exchange,
                "symbol": route_symbol,
                "candles": _warmup_candles,
                "timeframe": route_timeframe,
            }
        else:
            if jh.timeframe_to_one_minutes(route_timeframe) > jh.timeframe_to_one_minutes(trading_candles[key]["timeframe"]):
                trading_candles[key] = {
                    "exchange": route_exchange,
                    "symbol": route_symbol,
                    "candles": _trading_candles,
                    "timeframe": route_timeframe,
                }
                warmup_candles[key] = {
                    "exchange": route_exchange,
                    "symbol": route_symbol,
                    "candles": _warmup_candles,
                    "timeframe": route_timeframe,
                }
    return trading_candles, warmup_candles

# =============================================================================

if __name__ == "__main__":
    import logging, os
    os.environ['RAY_DISABLE_IMPORT_WARNING'] = '1'
    logging.getLogger('ray').setLevel(logging.ERROR)
    print("🚀 Starting Jesse Monte Carlo (candles + trades) Analysis")
    print("=" * 50)
    routes, data_routes = get_configured_routes()
    config = STRATEGY_CONFIG.copy(); config["exchange"] = TRADING_ROUTES[0]["exchange"]
    start_date = SIMULATION_CONFIG["start_date"]; end_date = SIMULATION_CONFIG["end_date"]; num_scenarios = SIMULATION_CONFIG["num_scenarios"]
    print(f"📋 Configuration:")
    print(f"   Trading Routes:")
    for route in TRADING_ROUTES:
        print(f"     {route['symbol']}@{route['timeframe']} ({route['strategy']})")
    print(f"   Data Routes:")
    if DATA_ROUTES:
        for route in DATA_ROUTES:
            print(f"     {route['symbol']}@{route['timeframe']}")
    else:
        print(f"     None (modify DATA_ROUTES at top of file to add)")
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Scenarios: {num_scenarios}")
    trading_candles, warmup_candles = prepare_candles_for_simulations(routes, data_routes, start_date, end_date, config)

    print(f"\n🎯 Running Monte Carlo (candles)...")
    mc_candles_results = monte_carlo_candles(
        config,
        routes,
        data_routes,
        progress_bar=SIMULATION_CONFIG["progress_bar"],
        candles=trading_candles,
        warmup_candles=warmup_candles,
        num_scenarios=num_scenarios,
        fast_mode=SIMULATION_CONFIG["fast_mode"],
        candles_pipeline_class=MONTE_CARLO_CANDLES_CONFIG["pipeline_class"],
        candles_pipeline_kwargs=MONTE_CARLO_CANDLES_CONFIG["pipeline_kwargs"],
    )
    print_monte_carlo_candles_summary(mc_candles_results)
    plot_monte_carlo_candles_chart(mc_candles_results)

    print(f"\n🎯 Running Monte Carlo (trades)...")
    monte_carlo_results = monte_carlo_trades(
        config,
        routes,
        data_routes,
        progress_bar=SIMULATION_CONFIG["progress_bar"],
        candles=trading_candles,
        warmup_candles=warmup_candles,
        num_scenarios=num_scenarios,
        benchmark=SIMULATION_CONFIG["benchmark"],
        fast_mode=SIMULATION_CONFIG["fast_mode"],
    )
    print_monte_carlo_trades_summary(monte_carlo_results)
    plot_monte_carlo_trades_chart(monte_carlo_results)

    print(f"\n✅ Analysis complete!")
    print("=" * 50)