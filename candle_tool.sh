#!/usr/bin/env bash
# candle-tool.sh — inspect / wipe / scan Jesse candle data (Postgres in docker)
#
# Usage:
#   ./candle-tool.sh inspect
#   ./candle-tool.sh wipe "<exchange>" "<symbol>"          # dry-run: shows what WOULD be deleted
#   ./candle-tool.sh wipe "<exchange>" "<symbol>" --yes    # actually deletes, then verifies count=0
#   ./candle-tool.sh scan "<exchange>" "<symbol>"          # zero-volume gap scan + PASS/FAIL verdict
#
# Workflow for the remediation (per ZERO-VOLUME-DIAGNOSIS.md):
#   1. ./candle-tool.sh inspect                # get the EXACT exchange/symbol strings stored in DB
#   2. Make sure the driver fix (fetch window clamp + retry-until-complete) is applied FIRST
#   3. ./candle-tool.sh wipe "<exchange>" "BTC-USD" --yes
#   4. Re-import BTC-USD via Jesse (sequential, single symbol). Expect ~45-55 min, NOT seconds.
#      If it finishes in seconds, the wipe didn't match — go back to step 1.
#   5. ./candle-tool.sh scan "<exchange>" "BTC-USD"        # must PASS before touching ETH/SOL

set -euo pipefail

PSQL='docker exec -i postgres psql -U jesse_user -d jesse_db -v ON_ERROR_STOP=1 -X -q'

# Thresholds for scan verdict (BTC/ETH/SOL perps should have essentially no dead HOURS)
MAX_DEAD_HOUR_PCT=2.0     # FAIL if more than 2% of hours have zero volume
MAX_DEAD_STREAK_H=3       # FAIL if any zero-volume streak >= 3 consecutive hours

cmd="${1:-}"

sql() { echo "$1" | $PSQL; }

case "$cmd" in

  inspect)
    echo "=== Exact (exchange, symbol) strings stored in the candle table ==="
    sql "
      SELECT exchange,
             symbol,
             timeframe,
             COUNT(*)                                        AS rows,
             to_timestamp(MIN(timestamp)/1000) AT TIME ZONE 'UTC' AS first_candle_utc,
             to_timestamp(MAX(timestamp)/1000) AT TIME ZONE 'UTC' AS last_candle_utc
      FROM candle
      GROUP BY exchange, symbol, timeframe
      ORDER BY exchange, symbol, timeframe;
    "
    echo
    echo ">>> Use the exchange/symbol strings EXACTLY as printed above for wipe/scan."
    ;;

  wipe)
    ex="${2:?usage: wipe \"<exchange>\" \"<symbol>\" [--yes]}"
    sym="${3:?usage: wipe \"<exchange>\" \"<symbol>\" [--yes]}"
    confirm="${4:-}"

    echo "=== Rows matching exchange='$ex' AND symbol='$sym' ==="
    sql "
      SELECT COUNT(*)                                        AS rows_to_delete,
             to_timestamp(MIN(timestamp)/1000) AT TIME ZONE 'UTC' AS first_candle_utc,
             to_timestamp(MAX(timestamp)/1000) AT TIME ZONE 'UTC' AS last_candle_utc
      FROM candle
      WHERE exchange = '$ex' AND symbol = '$sym';
    "

    n=$(echo "SELECT COUNT(*) FROM candle WHERE exchange = '$ex' AND symbol = '$sym';" | $PSQL -tA)
    if [ "$n" = "0" ]; then
      echo
      echo "!!! ZERO rows match. Your strings don't match what's in the DB."
      echo "!!! Run './candle-tool.sh inspect' and copy the strings exactly."
      exit 1
    fi

    if [ "$confirm" != "--yes" ]; then
      echo
      echo "DRY RUN ONLY — nothing deleted. Re-run with --yes to delete these $n rows."
      exit 0
    fi

    echo
    echo "Deleting $n rows..."
    sql "DELETE FROM candle WHERE exchange = '$ex' AND symbol = '$sym';"
    left=$(echo "SELECT COUNT(*) FROM candle WHERE exchange = '$ex' AND symbol = '$sym';" | $PSQL -tA)
    if [ "$left" = "0" ]; then
      echo "OK — 0 rows remain for ($ex, $sym). Safe to re-import."
      echo "Reminder: a genuine full re-import takes ~45-55 min. Seconds = something is wrong."
    else
      echo "!!! $left rows STILL remain after delete — investigate before importing."
      exit 1
    fi
    ;;

  scan)
    ex="${2:?usage: scan \"<exchange>\" \"<symbol>\"}"
    sym="${3:?usage: scan \"<exchange>\" \"<symbol>\"}"

    echo "=== Zero-volume gap scan for ($ex, $sym) — 1h aggregation of 1m candles ==="
    sql "
      WITH hourly AS (
        SELECT (timestamp / 3600000) * 3600000 AS h,
               SUM(volume) AS vol
        FROM candle
        WHERE exchange = '$ex' AND symbol = '$sym' AND timeframe = '1m'
        GROUP BY 1
      )
      SELECT COUNT(*)                                   AS total_hours,
             COUNT(*) FILTER (WHERE vol = 0)            AS dead_hours,
             ROUND(100.0 * COUNT(*) FILTER (WHERE vol = 0) / NULLIF(COUNT(*),0), 2) AS dead_pct
      FROM hourly;
    "

    echo
    echo "--- 10 longest zero-volume streaks (hours) ---"
    sql "
      WITH hourly AS (
        SELECT (timestamp / 3600000) * 3600000 AS h,
               SUM(volume) AS vol
        FROM candle
        WHERE exchange = '$ex' AND symbol = '$sym' AND timeframe = '1m'
        GROUP BY 1
      ),
      flagged AS (
        SELECT h, (vol = 0) AS dead,
               ROW_NUMBER() OVER (ORDER BY h)
             - ROW_NUMBER() OVER (PARTITION BY (vol = 0) ORDER BY h) AS grp
        FROM hourly
      )
      SELECT COUNT(*)                                            AS streak_hours,
             to_timestamp(MIN(h)/1000) AT TIME ZONE 'UTC'        AS streak_start_utc,
             to_timestamp(MAX(h)/1000) AT TIME ZONE 'UTC'        AS streak_end_utc
      FROM flagged
      WHERE dead
      GROUP BY grp
      ORDER BY streak_hours DESC
      LIMIT 10;
    "

    dead_pct=$(echo "
      WITH hourly AS (
        SELECT (timestamp / 3600000) * 3600000 AS h, SUM(volume) AS vol
        FROM candle
        WHERE exchange = '$ex' AND symbol = '$sym' AND timeframe = '1m'
        GROUP BY 1
      )
      SELECT COALESCE(ROUND(100.0 * COUNT(*) FILTER (WHERE vol = 0) / NULLIF(COUNT(*),0), 2), 100)
      FROM hourly;" | $PSQL -tA)

    max_streak=$(echo "
      WITH hourly AS (
        SELECT (timestamp / 3600000) * 3600000 AS h, SUM(volume) AS vol
        FROM candle
        WHERE exchange = '$ex' AND symbol = '$sym' AND timeframe = '1m'
        GROUP BY 1
      ),
      flagged AS (
        SELECT h, (vol = 0) AS dead,
               ROW_NUMBER() OVER (ORDER BY h)
             - ROW_NUMBER() OVER (PARTITION BY (vol = 0) ORDER BY h) AS grp
        FROM hourly
      )
      SELECT COALESCE(MAX(cnt), 0) FROM (
        SELECT COUNT(*) AS cnt FROM flagged WHERE dead GROUP BY grp
      ) s;" | $PSQL -tA)

    echo
    echo "=== VERDICT ==="
    echo "dead-hour rate: ${dead_pct}%  (threshold: ${MAX_DEAD_HOUR_PCT}%)"
    echo "longest streak: ${max_streak}h (threshold: ${MAX_DEAD_STREAK_H}h)"
    fail=0
    awk "BEGIN{exit !(${dead_pct} > ${MAX_DEAD_HOUR_PCT})}" && fail=1
    [ "${max_streak}" -ge "${MAX_DEAD_STREAK_H}" ] && fail=1
    if [ "$fail" = "1" ]; then
      echo "RESULT: FAIL — data still contains synthetic dead zones. Do NOT run research on this."
      exit 1
    else
      echo "RESULT: PASS — no significant synthetic dead zones detected."
    fi
    ;;

  *)
    echo "usage: $0 {inspect | wipe \"<exchange>\" \"<symbol>\" [--yes] | scan \"<exchange>\" \"<symbol>\"}"
    exit 1
    ;;
esac