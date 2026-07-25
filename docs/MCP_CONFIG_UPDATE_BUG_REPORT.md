# Bug report: `update_config` MCP tool silently fails to persist any change, and corrupts the stored config JSON

**Project:** Jesse (jesse-ai/project-template runtime, `jesse==2.5.0`)
**Files:**
- `jesse/mcp/tools/services/config.py` (`update_config_service`)
- `jesse/mcp/tools/config.py` (`update_config` MCP tool docstring/example)
- `jesse/modes/data_provider.py` (`update_config`, the actual DB-merge logic)

**Severity:** High — every config change made through the MCP `update_config` tool, following the tool's own documented workflow, silently no-ops while reporting `"status": "success"`, and pollutes the stored config with a garbage top-level key on every call.

---

## Summary

Calling the `update_config` MCP tool exactly as its own docstring instructs — `get_config()` → modify the returned object → `update_config(json.dumps(...))` — does not change **any** value in the database. It returns `{"status": "success", "message": "Configuration updated successfully"}`, but a subsequent `get_config()`/`get_backtest_config()` shows the old, unchanged values. Repeated calls also leave a stray, ever-overwritten top-level `"data"` key permanently sitting in the stored config JSON, unused by anything, alongside the real (untouched) config.

Root cause: a shape mismatch between what `get_config()` returns and what `update_config()`'s own documentation tells the caller to send back, combined with a merge function in `data_provider.py` that silently no-ops on structurally mismatched dicts instead of raising.

## Reproduction

1. `get_backtest_config()` → confirm `Kraken Pro Futures.futures_leverage` is e.g. `4`.
2. Follow the `update_config` tool's own documented example exactly:
   ```python
   current = get_config()
   config_data = current["config"]
   config_data["data"]["backtest"]["exchanges"]["Kraken Pro Futures"]["futures_leverage"] = 3
   # ^ this line from the tool's own docstring example
   update_config(json.dumps(config_data))
   ```
   (In practice: build the full config object under a `{"data": {...}}` root, as the tool's parameter docs explicitly require — *"Must follow Jesse configuration schema with 'data' root key"* — and call `update_config(json_string)`.)
3. Tool returns `{"status": "success", "message": "Configuration updated successfully"}`.
4. `get_backtest_config()` again → `Kraken Pro Futures.futures_leverage` is still `4`. **Silently unchanged.** Repeated retries produce the identical result every time.
5. Inspecting the raw DB row (`SELECT json FROM option WHERE type='config'`) confirms: the real config is untouched, and a new top-level `"data"` key has appeared, containing a full nested copy of the payload that was supposed to update it — inert, never read by anything.

## Root cause

**Shape mismatch, both sides self-inconsistent with the actual REST contract:**

- `get_config_service()` (`jesse/mcp/tools/services/config.py`) calls `POST /config/get`, which returns `{"data": <flat config>}`. The service then does `config = data.get('data', {})` — i.e. it **unwraps** the outer `"data"` key before returning. So `get_config()["config"]` is the **flat** config object (`backtest`, `monte_carlo`, etc. are top-level keys, no `"data"` wrapper).
- But `update_config`'s own MCP tool docstring (`jesse/mcp/tools/config.py`) says the parameter *"Must follow Jesse configuration schema with 'data' root key"*, and its own usage example explicitly does `config_data["data"]["backtest"][...] = ...` — i.e. it tells the caller to **re-wrap** the payload in a `"data"` key before saving it back. A caller who does exactly what `get_config()` returned, modifies it, and calls `update_config()` per the documented workflow ends up sending `{"data": {<the correctly modified flat config>}}` — an extra wrapper the backend never expects.
- `update_config_service()` forwards that payload as-is: `requests.post(f'{api_url}/config/update', json={'current_config': new_config})`, so `current_config` on the wire is `{"data": {...}}`.
- `config_controller.update_config()` passes `json_request.current_config` straight to `jesse/modes/data_provider.py::update_config(client_config)`.
- There, `existing = json.loads(o.json)` is the **flat** stored config (top-level keys `backtest`, `monte_carlo`, `optimization`, etc. — confirmed directly from the DB row). `client_config` is `{"data": {...}}` — a dict with a **single** top-level key, `"data"`, which does not exist in `existing`.
- `merged = jh.merge_dicts(existing, client_config)` — `merge_dicts` (in `jesse/helpers.py`) unions the top-level keys of both dicts and, for any key present in only one side, just copies it through unchanged (`elif k in dict1: yield k, dict1[k]` / `else: yield k, dict2[k]`). Since **no top-level key overlaps** between `existing` (`backtest`, `monte_carlo`, ...) and `client_config` (`data`), every real field from `existing` passes through **completely untouched**, and `client_config`'s lone `"data"` key gets tacked on as a new, unrelated top-level key.
- Net result: the write "succeeds" (valid JSON, HTTP 200), the real config is never modified, and the stored JSON accumulates a stray `"data"` key that grows/gets overwritten on every subsequent attempt but is never read by any consumer (`get_config_service()` only ever reads the real top-level keys via the REST API's own unwrapping, so this pollution is invisible until you look at the raw DB row).

This is a **self-inconsistent contract inside the MCP layer itself** — `get_config` and `update_config`'s own documented usage disagree about whether the "data" wrapper belongs at the `config` object's root, and `data_provider.update_config`'s merge has no validation to catch the mismatch and fail loudly instead of silently no-oping.

## Impact

- **Any** config change attempted through the MCP server via the documented `get_config()` → modify → `update_config()` workflow silently fails, every time, with no error surfaced anywhere.
- Every attempt leaves the DB config polluted with a growing/overwritten stray `"data"` key.
- This is not specific to `futures_leverage` or to Kraken — it affects every field in every section (`backtest`, `live`, `monte_carlo`, `optimization`, `significance_test`, `editor`), since the bug is structural (top-level shape mismatch), not field-specific.

## Fix options (pick one; either is sufficient on its own)

1. **Fix the tool's documentation/example** in `jesse/mcp/tools/config.py` to match what `get_config_service()` actually returns — i.e. drop the `"data"` root-key requirement, since `get_config()`'s output is already flat. Update the parameter docstring, the "Configuration Validation" note, and the usage example accordingly. This alone fixes the workflow for anyone following the documented example correctly, since `update_config_service()` would then forward the correctly-flat shape all the way through and `merge_dicts` would work as intended.
2. **Or**, if a `"data"`-wrapped root is actually intended as the contract (e.g. to match the dashboard's own request shape), fix `get_config_service()` to *not* unwrap the outer `"data"` key, so `get_config()` and `update_config()` agree on the same shape.
3. **Either way**, harden `jesse/modes/data_provider.py::update_config()` to fail loudly instead of silently no-oping on a structural mismatch — e.g. assert that `client_config`'s top-level keys are a subset of the known config sections (`backtest`, `live`, `monte_carlo`, `optimization`, `significance_test`, `editor`) before merging, and raise/return an error otherwise. This would have surfaced this exact bug immediately instead of requiring a raw DB inspection to catch it.

## Workaround used in the meantime

Wrote the desired change directly to the `option` table (`type='config'`) via a targeted `jsonb_set`, bypassing the MCP tool entirely, and manually removed the stray `"data"` pollution left behind by the failed attempts:

```sql
UPDATE option
SET json = jsonb_set(json::jsonb, '{backtest,exchanges,Kraken Pro Futures,futures_leverage}', '3')::text
WHERE type='config';

UPDATE option
SET json = (json::jsonb - 'data')::text
WHERE type='config';
```

Verified via `get_backtest_config()` / `get_config()` afterward that the running Jesse process reads config fresh from the DB on every call (no in-memory caching issue) — the direct DB write took effect immediately, confirming the bug is isolated to the `update_config` write path described above.
