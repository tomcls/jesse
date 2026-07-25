from jesse.research import import_candles
import time
from jesse.enums import exchanges

# # # # # # # # # # # # CONFIG # # # # # # # # # # # #
EXCHANGE = exchanges.BINANCE_PERPETUAL_FUTURES
SYMBOLS = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT','BNB-USDT','XRP-USDT','DOGE-USDT']

START_DATE = "2018-01-01" # Start date in YYYY-MM-DD format. 
# # # # # # # # # # # # END CONFIG # # # # # # # # # # # #

def fetch_candles(exchange, symbol, start_date):
    # Inform the user which symbol is being imported
    print(f"\n=== Importing candles for {symbol} ===")
    try:
        import_candles(exchange, symbol, start_date, show_progressbar=True)
        print(f"=== Finished importing candles for {symbol} ===\n")
        return True
    except ConnectionError as e:
        if '429' in str(e):
            print("Rate limit exceeded. Waiting for 1 minute.")
            time.sleep(60)  # Wait for 1 minute before retrying
        else:
            print("Network is down. Retrying in 5 minutes.")
            time.sleep(300)  # Wait for 5 minutes before retrying
        return False

# Run indefinitely
while True:
    for s in SYMBOLS:
        success = False
        while not success:
            success = fetch_candles(EXCHANGE, s, START_DATE)
            if not success:
                time.sleep(5)  # Wait for 5 Seconds before retrying

    print("Completed fetching candles for all symbols. Sleeping for 24 hours.")
    print("Current Date: ", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    time.sleep(86400)  # Sleep for 24 hours