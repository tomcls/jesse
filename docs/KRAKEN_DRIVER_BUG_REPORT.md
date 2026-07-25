Hello Saleh, im Tom.
i live n Europe so im obliged to use an exchange that has all EU legal stuffs.
And Kraken is currently the only candidate.

So while im using jesse with Kraken, Claude and I (more Claude than I to be honest) found some issues in the Kraken candles import.

# Bug report: Kraken Pro Futures candle-import driver silently corrupts historical data with synthetic zero-volume candles

**Project:** Jesse (jesse-ai/project-template runtime, `jesse==2.5.0`)
**File:** `jesse/modes/import_candles_mode/drivers/Kraken/KrakenPerpetualMain.py`
**Severity:** High — silently produces bad historical data that looks valid (no error, no warning) and cannot be repaired by re-running the import.

---

## Summary

`KrakenPerpetualMain.fetch()` requests a fixed 5000-minute window per call but never checks
whether the Kraken Futures charts API actually returned that many candles. The API hard-caps
a single response at roughly **2000 candles**, regardless of the requested `from`/`to` span.
The unfilled remainder of every chunk is silently accepted as "no more candles" and gets
permanently backfilled by Jesse core's `_fill_absent_candles()` with flat,
`open=high=low=close=<last_close>, volume=0` synthetic candles. Because import writes use
`Candle.insert_many(...).on_conflict_ignore()` and the "already imported" check
(`jesse/modes/import_candles_mode/__init__.py`) is purely row-count-based, this corruption is
**permanent** — running `import_candles` again, any number of times, never re-checks or
repairs it.

On a real install with ~4.3 years of BTC/ETH/SOL history imported via this driver, **~59% of
all 1-hour periods** ended up completely flat / zero-volume as a result — not confined to a
short window, spread evenly across the entire imported history. The underlying trade data is
real and available on Kraken's side the whole time; nothing is actually missing from the
exchange.

## Environment

- `jesse==2.5.0`, editable install
- Exchange: Kraken Pro Futures (`KRAKEN_PERPETUAL`), also present (unverified, likely same
  bug) in `KrakenPerpetualTestnet`
- Symbol tested: `BTC-USD` (`PF_XBTUSD`), also reproduced on `ETH-USD` (`PF_ETHUSD`)
- Postgres candle store, `docker exec ... psql` used for verification queries below

## Symptom

Querying the stored `candle` table for `(Kraken Pro Futures, BTC-USD, 1m)` and aggregating
into 1-hour buckets:

- 59.1% of all hours over 4.3 years of imported history have **zero total volume** — every
  underlying 1-minute row in that hour is `open=high=low=close`, `volume=0`.
- The rate is essentially identical across BTC-USD, ETH-USD, and SOL-USD (58.9%–59.3%)
  despite very different real-world liquidity — a strong signal this is mechanical, not
  organic thin trading.
- Longest observed streak: 51 consecutive dead hours.
- The dead-hour rate is flat across every hour-of-day (58.9%–59.2% for every UTC hour) —
  real markets have strong diurnal volume patterns; this flatness by itself rules out
  genuine illiquidity.
- Streak start times land with **exact, zero-variance periodicity**: every 10.4167 days for
  BTC-USD's import history, every 3.4722 days for ETH-USD's. Both are exact integer
  multiples of the driver's own chunk size (`count=5000` minutes = 3.4722 days). This
  periodicity was the first strong clue that the bug tracked the driver's own request
  boundaries rather than anything about the market.

## Root cause

### 1. `fetch()` requests 5000 minutes but never validates the response size

```python
def fetch(self, symbol: str, start_timestamp: int, timeframe: str = '1m') -> Union[list, None]:
    k_symbol = self._jesse_to_kraken_symbol(symbol)
    resolution = timeframe_to_futures_resolution(timeframe)
    one_min = jh.timeframe_to_one_minutes(timeframe)
    from_sec = int(start_timestamp / 1000)
    to_sec = from_sec + (self.count * one_min * 60)   # count = 5000

    url = f'{self.endpoint}/api/charts/v1/trade/{k_symbol}/{resolution}'
    response = self.session.get(url, params={'from': from_sec, 'to': to_sec}, timeout=15)
    self.validate_response(response)
    candles = response.json().get('candles', [])       # <- accepted as-is, whatever size
    ...
```

Confirmed independently of Jesse with a plain `curl` (no auth needed) that the endpoint
truncates a 5001-minute request down to exactly 2000 candles:

```
$ curl -s "https://futures.kraken.com/api/charts/v1/trade/PF_XBTUSD/1m?from=1648771200&to=1649030100"
# requested window: 2022-04-01T00:00:00 -> 2022-04-04T11:20:00 (5001 minutes)
# → 2000 candles returned, covering only up to 2022-04-02T09:19:00
```

`self.count = 5000` (set in `__init__`) is simply larger than what the endpoint will ever
return in one call. `fetch()` has no pagination and no length check, so every chunk request
silently gets truncated to ~2000 real candles + (up to) ~3000 minutes worth of "missing"
range that the caller has no way to know about.

### 2. `fetch()` also ignores the caller's "don't request the future" clamp

The main import loop (`import_candles_mode/__init__.py`) computes and clamps
`temp_end_timestamp` to "now" before calling `_fill_absent_candles`, but never passes that
clamp into `driver.fetch()`. `fetch()` independently recomputes `to_sec = from_sec +
count*60s`, so the last chunk of any import can legitimately request a still-in-the-future
window, compounding the truncation problem for the most recent data specifically.

### 3. The permanent-corruption mechanism (Jesse core, not Kraken-specific)

This is the part that turns a per-request quirk into unrecoverable data loss, and it isn't
specific to this driver — any driver that returns a short response for any reason (rate
limit, transient network blip, a response-size cap like this one) hits the same trap:

- `_fill_absent_candles()` (`import_candles_mode/__init__.py`) walks the requested chunk
  minute-by-minute and synthesizes a flat `volume=0` candle for every timestamp not present
  in whatever `fetch()` returned — it has no way to distinguish "the exchange genuinely had
  no trade this minute" from "the driver's response got truncated".
- The next-chunk "already imported" check is purely count-based:
  `already_exists = (existing row count in this timestamp range) == driver.count`. A chunk
  that's 100% synthetically filled has exactly `driver.count` rows — indistinguishable from a
  correct one.
- `store_candles_list()` inserts with `Candle.insert_many(candles).on_conflict_ignore()` —
  once a row exists at `(exchange, symbol, timeframe, timestamp)`, nothing ever overwrites it.

Net effect: the **first** time a chunk gets truncated, the shortfall is permanently frozen as
fake data. Re-running `import_candles` — even a hundred times — will never detect or repair
it, because the row count already matches what's expected.

## Impact

- Any indicator computed continuously across a corrupted multi-hour block (EMA, ATR, etc.)
  gets anchored to a stale flat price for the entire block, and that distortion bleeds into
  the real data immediately following it.
- Since this is baked into ~59% of the whole imported history (not one bad batch), the
  existing dataset for any symbol imported through this driver is not usable for backtesting
  as-is and needs to be wiped and re-imported after the fix.
- Backtests still "run" without any error — this is the dangerous part; nothing surfaces to
  the user that anything is wrong.

## Fix

Patch against the current `KrakenPerpetualMain.py` (only this file touched):

1. Clamp the request window to never extend past "now" (minus the in-progress minute).
2. Real pagination: after a page comes back, if it's non-empty, advance the cursor to right
   after the last candle received and request the remaining window again — a page shorter
   than what's left is expected mid-pagination given the ~2000 cap, not a failure.
3. Wrap the full pagination pass in a retry-with-backoff (5 attempts, 2/4/8/16s) for the case
   a page comes back short for a reason other than the known cap (e.g. a transient blip). If
   still short after retries, **raise** instead of returning a partial list — never let a
   known-incomplete result reach `_fill_absent_candles`.

```diff
--- a/jesse/modes/import_candles_mode/drivers/Kraken/KrakenPerpetualMain.py
+++ b/jesse/modes/import_candles_mode/drivers/Kraken/KrakenPerpetualMain.py
@@ -1,3 +1,5 @@
+import time
+
 import requests
 from requests.adapters import HTTPAdapter
 from urllib3.util.retry import Retry
@@ -16,9 +18,20 @@
         https://futures.kraken.com/api/charts/v1/trade/<symbol>/<resolution>?from=&to=
     `time` in the response is in MILLISECONDS and is the OPENING time of the candle.
     `from`/`to` query params are in SECONDS. The endpoint serves deep history (BTC perp
-    1m data goes back well over a month, daily back years), but info.py keeps backtesting
-    disabled by default until the per-pair 1m depth is fully validated. The live runtime
-    still uses this driver to fetch warm-up candles.
+    1m data goes back well over a month, daily back years). The live runtime still uses
+    this driver to fetch warm-up candles.
+
+    2026-07-22: root-caused a data-loss bug. This endpoint hard-caps a single request at
+    ~2000 candles regardless of the `from`/`to` span requested (confirmed independently of
+    Jesse with a plain curl) — `fetch()` used to request `count` (5000) candles in one call
+    and silently accept whatever partial page came back. Jesse core's
+    `_fill_absent_candles()` + `on_conflict_ignore` inserts then permanently froze synthetic
+    zero-volume placeholders over the untrusted tail of every chunk, with no way to self-heal
+    on re-import. Fixed by (1) clamping the request window to never extend past "now", (2)
+    real pagination — follow the server's own page size forward until the full window is
+    covered, and (3) wrapping that in a retry-with-backoff for the rare case a page is short
+    for a reason other than the known size cap (never silently hand a knowingly-incomplete
+    result downstream).
     """
 
     def __init__(self, name: str, rest_endpoint: str) -> None:
@@ -60,17 +73,92 @@
         # `time` is already ms and is the candle open time
         return int(candles[0]['time'])
 
+    # retry-until-complete tuning for fetch() below
+    _FETCH_MAX_ATTEMPTS = 5
+    _FETCH_BACKOFF_SECONDS = [2, 4, 8, 16]
+    # safety bound on pages-per-attempt; the API caps a single page at ~2000 candles,
+    # so covering one 5000-minute chunk needs ~3 pages - this is a generous multiple
+    # of that to tolerate a smaller-than-expected page without false-tripping.
+    _FETCH_MAX_PAGES_PER_ATTEMPT = 15
+
+    def _fetch_page_range(self, url: str, from_sec: int, to_sec: int, step_sec: int) -> list:
+        """
+        Page forward through [from_sec, to_sec], following whatever page size the
+        server actually returns (confirmed to hard-cap around ~2000 candles per
+        request, independent of how wide `from`/`to` is). A page shorter than the
+        remaining window is normal mid-pagination, not a failure - we just advance
+        the cursor to right after the last candle we got and ask again. Stops when
+        we've covered up to `to_sec`, or the server returns nothing more to give.
+        """
+        all_candles = []
+        cursor = from_sec
+        pages = 0
+        while cursor <= to_sec and pages < self._FETCH_MAX_PAGES_PER_ATTEMPT:
+            pages += 1
+            response = self.session.get(url, params={'from': cursor, 'to': to_sec}, timeout=15)
+            self.validate_response(response)
+            page = response.json().get('candles', [])
+            if not page:
+                break
+            all_candles.extend(page)
+            last_sec = int(page[-1]['time']) // 1000
+            next_cursor = last_sec + step_sec
+            if next_cursor <= cursor:
+                break  # safety: no forward progress, avoid looping forever
+            cursor = next_cursor
+        return all_candles
+
     def fetch(self, symbol: str, start_timestamp: int, timeframe: str = '1m') -> Union[list, None]:
         k_symbol = self._jesse_to_kraken_symbol(symbol)
         resolution = timeframe_to_futures_resolution(timeframe)
         one_min = jh.timeframe_to_one_minutes(timeframe)
-        from_sec = int(start_timestamp / 1000)
-        to_sec = from_sec + (self.count * one_min * 60)
+        step_sec = one_min * 60
+        # Kraken candles are aligned to the resolution grid (open times are exact
+        # multiples of step_sec) - align from_sec down so expected_count below matches
+        # what the API can actually return, regardless of caller alignment.
+        from_sec = (int(start_timestamp / 1000) // step_sec) * step_sec
+        to_sec = from_sec + (self.count * step_sec)
+
+        # never request a range extending past "now" (minus the still-in-progress minute) -
+        # asking for a genuinely future window guarantees a short response that would
+        # otherwise get permanently zero-filled by _fill_absent_candles downstream.
+        now_sec = jh.now_to_timestamp() // 1000
+        max_to_sec = ((now_sec - 60) // step_sec) * step_sec
+        if max_to_sec < from_sec:
+            # the entire requested window is still in the future; nothing to fetch yet
+            return []
+        to_sec = min(to_sec, max_to_sec)
+
+        expected_count = (to_sec - from_sec) // step_sec + 1
 
         url = f'{self.endpoint}/api/charts/v1/trade/{k_symbol}/{resolution}'
-        response = self.session.get(url, params={'from': from_sec, 'to': to_sec}, timeout=15)
-        self.validate_response(response)
-        candles = response.json().get('candles', [])
+        candles = []
+        for attempt in range(1, self._FETCH_MAX_ATTEMPTS + 1):
+            candles = self._fetch_page_range(url, from_sec, to_sec, step_sec)
+
+            if len(candles) >= expected_count:
+                break
+
+            is_last_attempt = attempt == self._FETCH_MAX_ATTEMPTS
+            print(
+                f'[KrakenPerpetualMain] short candle range for {symbol} {resolution} '
+                f'{jh.timestamp_to_time(from_sec * 1000)[:19]} -> {jh.timestamp_to_time(to_sec * 1000)[:19]} '
+                f'(attempt {attempt}/{self._FETCH_MAX_ATTEMPTS}, after pagination): '
+                f'expected {expected_count}, got {len(candles)}.'
+                + (' Giving up.' if is_last_attempt
+                   else f' Retrying in {self._FETCH_BACKOFF_SECONDS[attempt - 1]}s...')
+            )
+
+            if is_last_attempt:
+                raise exceptions.CandleNotFoundInExchange(
+                    f'Kraken Pro Futures returned an incomplete candle set for {symbol} {resolution} '
+                    f'{jh.timestamp_to_time(from_sec * 1000)[:19]} -> {jh.timestamp_to_time(to_sec * 1000)[:19]} '
+                    f'after {self._FETCH_MAX_ATTEMPTS} full-pagination attempts '
+                    f'(expected {expected_count}, got {len(candles)}). '
+                    'Refusing to silently hand this gap downstream to be filled with synthetic candles.'
+                )
+
+            time.sleep(self._FETCH_BACKOFF_SECONDS[attempt - 1])
 
         # `time` is in MILLISECONDS and is the candle open time -> use as-is. Oldest-first.
         return [
```

### A broader hardening suggestion for Jesse core (not included in the patch above)

The permanent-corruption mechanism (§3) is generic to `import_candles_mode`, not specific to
this driver. Any driver that ever returns a short response — for a rate limit, a network
blip, an exchange-side outage, or a cap like this one — will have the shortfall permanently
frozen as fake data with no self-healing path, because:

- the "already imported" check only counts rows, never validates them, and
- inserts are `on_conflict_ignore`, so nothing can ever be corrected in place short of
  manually deleting the affected rows first.

Two independent, non-Kraken-specific improvements worth considering:
1. Make `_fill_absent_candles()` mark synthetic rows distinctly (a boolean column, or a
   sentinel value) so they can be identified and safely re-fetched later instead of looking
   identical to real data forever.
2. Don't let a chunk containing synthetic rows satisfy the count-based "already imported"
   check on a subsequent `import_candles` run — right now, a corrupted import can never be
   healed by simply re-running the same command a user would naturally try.

## Validation

After applying the patch and wiping + re-importing `BTC-USD` from scratch:
- The chunk that previously failed after 5 retries (`2022-04-01T00:00:00 →
  2022-04-04T11:20:00`, expected 5001, got 2000) now returns the full 5001 candles in 0.3s
  across 3 pages.
- 0 fully zero-volume hours in that chunk (isolated zero-volume single-minute candles remain,
  which is expected/normal — the problem was full-hour dead blocks, not sparse minutes).
- Regression-checked: a genuinely future request window still returns `[]` immediately with
  no wasted retries; a non-minute-aligned `start_timestamp` no longer causes a spurious
  false-positive short-response error.

Happy to open this as a proper GitHub issue / PR against the repo if that's preferred over a
written report — let me know which you'd rather have.
