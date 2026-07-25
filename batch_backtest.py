import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any
import jesse.helpers as jh
from jesse.research import backtest, get_candles
from jesse.enums import exchanges
import pandas as pd
import ray
from multiprocessing import cpu_count
from tqdm import tqdm

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Configuration 
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
STRATEGY_NAME = "MeanReversionRSI"  # Replace with your strategy name
EXCHANGE_NAME = exchanges.BINANCE_PERPETUAL_FUTURES # Replace with your exchange name
SYMBOLS = [
    'BTC-USDT', 'ETH-USDT',
    'BNB-USDT', 'SOL-USDT',
    'XRP-USDT', 'DOGE-USDT', 'BNB-USDT',
    # 'BCH-USDT', 'LTC-USDT',
    # 'XLM-USDT', 'XMR-USDT',
    # 'TRX-USDT', 'FARTCOIN-USDT',
    # '1000PEPE-USDT', 'SUI-USDT',
]  # List of symbols to test
TIMEFRAMES = [
    # "3m", "5m", "15m", "30m", "1h"
    "15m", "30m", "1h"
]  # List of timeframes to test
START_DATE = "2022-01-01"  # Start date in YYYY-MM-DD format
END_DATE = "2025-11-09"  # End date in YYYY-MM-DD format

# Route Configuration - modify these to customize your data routes
DATA_ROUTES = [
    # Add more data routes as needed, for example:
    {"symbol": "SOL-USDT", "timeframe": "4h"},
    # {"symbol": "SOL-USDT", "timeframe": "4h"},
    # {"symbol": "BTC-USDT", "timeframe": "4h"},
]

# Default config - modify as needed
CONFIG = {
    # Required keys for jesse.research.backtest()
    'starting_balance': 10_000,       # Starting balance for the account
    'fee': 0.0007,                    # Trading fee (e.g. 0.07%)
    'type': 'futures',                # Exchange type (spot / futures)
    'futures_leverage': 10,           # Leverage
    'futures_leverage_mode': 'cross', # Leverage mode
    'exchange': EXCHANGE_NAME,        # Exchange enum value
    'warm_up_candles': 210,           # Warm-up candles
}
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 



def create_routes(strategy_name: str, exchange_name: str, symbol: str, timeframe: str):
    routes = [
        {'exchange': exchange_name, 'strategy': strategy_name, 'symbol': symbol, 'timeframe': timeframe}
    ]

    # Create data routes from the configured DATA_ROUTES list
    # Users can modify the DATA_ROUTES variable at the top of the file
    data_routes = [
        {'exchange': exchange_name, 'symbol': route['symbol'], 'timeframe': route['timeframe']}
        for route in DATA_ROUTES
    ]

    return routes, data_routes


def fetch_and_prepare_data(exchange_name: str, symbol: str, timeframe: str, 
                          start_date_str: str, finish_date_str: str, config: dict):
    # Include the primary timeframe and all data timeframes from configuration
    # Users can modify the DATA_ROUTES variable at the top of the file
    data_timeframes = [route['timeframe'] for route in DATA_ROUTES]
    timeframes_list = [timeframe] + data_timeframes
    max_timeframe = jh.max_timeframe(timeframes_list)

    # Fetch the raw candle data for the trading symbol
    warmup_candles_raw, trading_candles_raw = get_candles(
        exchange_name, symbol, max_timeframe, jh.date_to_timestamp(start_date_str), 
        jh.date_to_timestamp(finish_date_str), config['warm_up_candles'], 
        caching=True, is_for_jesse=True
    )

    # Prepare data in the format expected by jesse.research.backtest
    trading_candles = {
        jh.key(exchange_name, symbol): {
            'exchange': exchange_name,
            'symbol': symbol,
            'candles': trading_candles_raw,
        },
    }
    
    warmup_candles = {
        jh.key(exchange_name, symbol): {
            'exchange': exchange_name,
            'symbol': symbol,
            'candles': warmup_candles_raw,
        },
    }
    
    # Fetch data for all symbols in DATA_ROUTES (if different from trading symbol)
    data_symbols = {route['symbol'] for route in DATA_ROUTES}  # Get unique symbols
    for data_symbol in data_symbols:
        if data_symbol != symbol:  # Only fetch if different from trading symbol
            data_warmup_raw, data_trading_raw = get_candles(
                exchange_name, data_symbol, max_timeframe, jh.date_to_timestamp(start_date_str), 
                jh.date_to_timestamp(finish_date_str), config['warm_up_candles'], 
                caching=True, is_for_jesse=True
            )
            
            # Add data symbol data to the candles dictionaries
            trading_candles[jh.key(exchange_name, data_symbol)] = {
                'exchange': exchange_name,
                'symbol': data_symbol,
                'candles': data_trading_raw,
            }
            
            warmup_candles[jh.key(exchange_name, data_symbol)] = {
                'exchange': exchange_name,
                'symbol': data_symbol,
                'candles': data_warmup_raw,
            }
    
    return trading_candles, warmup_candles


def execute_strategy(
        strategy_name: str,
        exchange_name: str,
        symbol: str,
        timeframe: str,
        config: dict,
        start_date_str: str,
        finish_date_str: str
):
    # Create routes for trading and data
    routes, data_routes = create_routes(strategy_name, exchange_name, symbol, timeframe)
    
    # Fetch and prepare the candle data
    trading_candles, warmup_candles = fetch_and_prepare_data(
        exchange_name, symbol, timeframe, start_date_str, finish_date_str, config
    )

    # Execute the backtest
    result = backtest(
        config,
        routes,
        data_routes,
        candles=trading_candles,
        warmup_candles=warmup_candles,
        generate_equity_curve=False,  # Set to False to avoid the error
        generate_csv=False,  # Don't generate files
        generate_json=False,
        generate_logs=False,
        fast_mode=True
    )

    return result


@ray.remote
def ray_execute_strategy(
        strategy_name: str,
        exchange_name: str,
        symbol: str,
        timeframe: str,
        config: dict,
        start_date_str: str,
        finish_date_str: str,
        task_id: int
):
    """
    Execute a single backtest as a Ray remote task
    """
    try:
        result = execute_strategy(
            strategy_name=strategy_name,
            exchange_name=exchange_name,
            symbol=symbol,
            timeframe=timeframe,
            config=config,
            start_date_str=start_date_str,
            finish_date_str=finish_date_str
        )
        
        return {
            'result': result,
            'symbol': symbol,
            'timeframe': timeframe,
            'task_id': task_id,
            'log': None
        }
    except Exception as e:
        error_msg = f"Task {task_id} failed for {symbol}/{timeframe}: {str(e)}"
        return {
            'result': None,
            'symbol': symbol,
            'timeframe': timeframe,
            'task_id': task_id,
            'log': error_msg,
            'error': True
        }


def batch_backtest(
        strategy_name: str,
        exchange_name: str,
        symbols: List[str],
        timeframes: List[str],
        start_date: str,
        end_date: str,
        config: Dict = None,
        progress_bar: bool = True,
        cpu_cores: int = None
) -> Dict[str, Dict[str, Any]]:
    """
    Run backtests for multiple symbols and timeframes in parallel
    """
    if config is None:
        config = CONFIG
        
    # Determine the number of CPU cores to use, if not specified, use 80% of available cores
    if cpu_cores is None:
        available_cores = cpu_count()
        # Use 80% of available cores by default, but at least 1
        cpu_cores = max(1, int(available_cores * 0.8))
    else:
        # Make sure cpu_cores is at least 1 and not more than available
        available_cores = cpu_count()
        cpu_cores = max(1, min(cpu_cores, available_cores))
    
    # Initialize Ray if not already initialized
    if not ray.is_initialized():
        try:
            ray.init(num_cpus=cpu_cores, ignore_reinit_error=True)
            print(f"Successfully initialized parallel processing with {cpu_cores} CPU cores")
        except Exception as e:
            print(f"Error initializing Ray: {e}. Falling back to sequential mode.")
            # Fall back to sequential processing
            return sequential_batch_backtest(
                strategy_name=strategy_name,
                exchange_name=exchange_name,
                symbols=symbols,
                timeframes=timeframes,
                start_date=start_date,
                end_date=end_date,
                config=config,
                progress_bar=progress_bar
            )
    
    try:
        total_backtests = len(symbols) * len(timeframes)
        print(f"Launching {total_backtests} backtests in parallel...")
        
        # Launch all tasks in parallel
        refs = []
        task_id = 0
        for symbol in symbols:
            for timeframe in timeframes:
                ref = ray_execute_strategy.remote(
                    strategy_name=strategy_name,
                    exchange_name=exchange_name,
                    symbol=symbol,
                    timeframe=timeframe,
                    config=config,
                    start_date_str=start_date,
                    finish_date_str=end_date,
                    task_id=task_id
                )
                refs.append(ref)
                task_id += 1
        
        # Initialize progress bar if requested
        if progress_bar:
            pbar = tqdm(total=total_backtests, desc="Backtesting Progress")
        else:
            pbar = None
            
        # Process results as they complete
        results = {}
        metrics_data = []
        total_completed = 0
        
        while refs:
            # Wait for any task to complete (with timeout for responsiveness)
            done_refs, refs = ray.wait(refs, num_returns=1, timeout=0.5)
            
            if done_refs:
                for ref in done_refs:
                    # Get and process result
                    try:
                        response = ray.get(ref)
                        
                        symbol = response['symbol']
                        timeframe = response['timeframe']
                        
                        # Initialize the symbol dict if not exists
                        if symbol not in results:
                            results[symbol] = {}
                        
                        # Add the result
                        if response['result'] is not None:
                            results[symbol][timeframe] = response['result']
                            
                            # Extract key metrics
                            metrics = response['result'].get('metrics', {}) or {}
                            
                            metrics_data.append({
                                'Symbol': symbol,
                                'Timeframe': timeframe,
                                'Total Trades': metrics.get('total', 0),
                                'Win Rate': metrics.get('win_rate', 0) * 100,  # convert to %
                                'Return %': metrics.get('net_profit_percentage', 0),
                                'Annual Return %': metrics.get('annual_return', 0),
                                'Max Drawdown %': metrics.get('max_drawdown', 0),
                                'Sharpe Ratio': metrics.get('sharpe_ratio', 0),
                                'Sortino Ratio': metrics.get('sortino_ratio', 0),
                                'Calmar Ratio': metrics.get('calmar_ratio', 0),
                                'Winning Streak': metrics.get('winning_streak', 0),
                                'Losing Streak': metrics.get('losing_streak', 0),
                                'Avg Win': metrics.get('average_win', 0),
                                'Avg Loss': metrics.get('average_loss', 0),
                            })
                        
                        # Print log messages
                        if response.get('log'):
                            if pbar:
                                tqdm.write(response['log'])
                            else:
                                print(response['log'])
                        
                    except Exception as e:
                        if pbar:
                            tqdm.write(f"Error processing result: {str(e)}")
                        else:
                            print(f"Error processing result: {str(e)}")
                    
                    # Update progress bar
                    if pbar:
                        pbar.update(1)
                    total_completed += 1
        
        if pbar:
            pbar.close()
        
        # Create a pandas DataFrame from the results
        df = pd.DataFrame(metrics_data)
        
        # Display results only if there is data
        if not df.empty:
            visualize_results(df)
        else:
            print("No metrics collected. Please check strategy or data.")
        
        return results
    
    except Exception as e:
        print(f"Error during batch backtest: {e}")
        raise
    
    finally:
        # Shutdown Ray
        if ray.is_initialized():
            ray.shutdown()


def sequential_batch_backtest(
        strategy_name: str,
        exchange_name: str,
        symbols: List[str],
        timeframes: List[str],
        start_date: str,
        end_date: str,
        config: dict,
        progress_bar: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Run backtests sequentially as fallback when parallel execution fails
    """
    results = {}
    metrics_data: List[Dict[str, Any]] = []
    
    total_backtests = len(symbols) * len(timeframes)
    
    if progress_bar:
        iterator = tqdm(range(total_backtests), desc="Sequential Backtests")
    else:
        iterator = range(total_backtests)
    
    count = 0
    for symbol in symbols:
        results[symbol] = {}
        for timeframe in timeframes:
            if progress_bar:
                tqdm.write(f"Running backtest {count+1}/{total_backtests}: {symbol} on {timeframe} timeframe...")
            else:
                print(f"Running backtest {count+1}/{total_backtests}: {symbol} on {timeframe} timeframe...")
            
            try:
                result = execute_strategy(
                    strategy_name=strategy_name,
                    exchange_name=exchange_name,
                    symbol=symbol,
                    timeframe=timeframe,
                    config=config,
                    start_date_str=start_date,
                    finish_date_str=end_date
                )
                
                results[symbol][timeframe] = result
                
                # Extract key metrics (safe access with .get)
                metrics = result.get('metrics', {}) or {}

                metrics_data.append({
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Total Trades': metrics.get('total', 0),
                    'Win Rate': metrics.get('win_rate', 0) * 100,  # convert to %
                    'Return %': metrics.get('net_profit_percentage', 0),
                    'Annual Return %': metrics.get('annual_return', 0),
                    'Max Drawdown %': metrics.get('max_drawdown', 0),
                    'Sharpe Ratio': metrics.get('sharpe_ratio', 0),
                    'Sortino Ratio': metrics.get('sortino_ratio', 0),
                    'Calmar Ratio': metrics.get('calmar_ratio', 0),
                    'Winning Streak': metrics.get('winning_streak', 0),
                    'Losing Streak': metrics.get('losing_streak', 0),
                    'Avg Win': metrics.get('average_win', 0),
                    'Avg Loss': metrics.get('average_loss', 0),
                })
            except Exception as e:
                if progress_bar:
                    tqdm.write(f"Error in backtest for {symbol}/{timeframe}: {str(e)}")
                else:
                    print(f"Error in backtest for {symbol}/{timeframe}: {str(e)}")
            
            if progress_bar:
                iterator.update(1)
            count += 1
    
    # Create a pandas DataFrame from the results
    df = pd.DataFrame(metrics_data)
    
    # Display results only if there is data
    if not df.empty:
        visualize_results(df)
    else:
        print("No metrics collected. Please check strategy or data.")
    
    return results


def visualize_results(df):
    """
    Visualize the backtest results using tables and charts
    """
    # Sort the dataframe by Sharpe Ratio (descending) before displaying
    df_sorted = df.sort_values(by='Sharpe Ratio', ascending=False).reset_index(drop=True)
    
    # Display a summary table of all results
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    print("\n===== BACKTEST RESULTS (Sorted by Sharpe Ratio) =====")
    print(df_sorted)
    
    # Create heatmaps for key metrics
    create_heatmaps(df)
    
    # Create bar charts for comparing performance
    create_performance_charts(df)


def create_heatmaps(df):
    """
    Create heatmaps for visualizing the results
    """
    metrics_to_plot = ['Return %', 'Win Rate', 'Sharpe Ratio', 'Max Drawdown %']
    
    # Create a figure with subplots for each metric - reduced size
    plt.figure(figsize=(12, 8))
    
    for i, metric in enumerate(metrics_to_plot):
        plt.subplot(2, 2, i+1)
        
        # Sort symbols by their average metric value
        symbol_order = df.groupby('Symbol')[metric].mean().sort_values(ascending=False).index.tolist()
        
        # Sort timeframes by their average metric value
        timeframe_order = df.groupby('Timeframe')[metric].mean().sort_values(ascending=False).index.tolist()
        
        # Reshape data for heatmap (symbol vs timeframe) with custom ordering
        pivot_df = df.pivot(index='Symbol', columns='Timeframe', values=metric)
        
        # Reorder the rows and columns based on performance
        pivot_df = pivot_df.reindex(index=symbol_order, columns=timeframe_order)
        
        # Create the heatmap
        if metric == 'Max Drawdown %':
            # For drawdown, more negative (larger drawdowns) should be red
            sns.heatmap(pivot_df, annot=True, cmap='RdYlGn', fmt='.2f', linewidths=.5)
        else:
            # For other metrics, higher values are better (green)
            sns.heatmap(pivot_df, annot=True, cmap='RdYlGn', fmt='.2f', linewidths=.5)
        
        plt.title(f'{metric} by Symbol and Timeframe (Sorted by Performance)')
    
    plt.tight_layout()
    plt.show()


def create_performance_charts(df):
    """
    Create bar charts for comparing performance
    """
    # Sort the dataframe by the metrics we're plotting
    df_return = df.sort_values(by='Return %', ascending=False)
    df_sharpe = df.sort_values(by='Sharpe Ratio', ascending=False)
    
    # Reduced figure size
    plt.figure(figsize=(12, 6))
    
    # Total Return by Symbol and Timeframe (sorted)
    plt.subplot(1, 2, 1)
    chart = sns.barplot(x='Symbol', y='Return %', hue='Timeframe', data=df_return)
    chart.set_title('Net Profit % by Symbol and Timeframe')
    chart.set_ylabel('Net Profit (%)')
    plt.xticks(rotation=45)
    
    # Sharpe Ratio by Symbol and Timeframe (sorted)
    plt.subplot(1, 2, 2)
    chart = sns.barplot(x='Symbol', y='Sharpe Ratio', hue='Timeframe', data=df_sharpe)
    chart.set_title('Sharpe Ratio by Symbol and Timeframe')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.show()
    
    # Win Rate vs Max Drawdown - reduced figure size
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(df['Win Rate'], 
               df['Max Drawdown %'], 
               s=df['Total Trades'] * 5,  # Size based on number of trades
               c=df['Return %'],      # Color based on return
               cmap='RdYlGn', 
               alpha=0.7)
    
    plt.colorbar(scatter, label='Total Return (%)')
    plt.xlabel('Win Rate')
    plt.ylabel('Max Drawdown (%)')
    plt.title('Win Rate vs Max Drawdown (size = number of trades, color = return)')
    
    # Add labels for each point
    for i, row in df.iterrows():
        plt.annotate(f"{row['Symbol']} {row['Timeframe']}", 
                    (row['Win Rate'], row['Max Drawdown %']),
                    xytext=(5, 5), 
                    textcoords='offset points')
    
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    print(f"Running batch backtests for:")
    print(f"Strategy: {STRATEGY_NAME}")
    print(f"Symbols: {SYMBOLS}")
    print(f"Timeframes: {TIMEFRAMES}")
    print(f"Period: {START_DATE} to {END_DATE}")
    
    # Run batch backtest with parallel processing
    results = batch_backtest(
        strategy_name=STRATEGY_NAME,
        exchange_name=EXCHANGE_NAME,
        symbols=SYMBOLS,
        timeframes=TIMEFRAMES,
        start_date=START_DATE,
        end_date=END_DATE,
        config=CONFIG,
        progress_bar=True
    )
    