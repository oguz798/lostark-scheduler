# Lost Ark Scheduler Status Report

Date: 2026-05-01

## Current State

The project has now moved fully to NiceGUI for the frontend layer. The old FastAPI/Jinja page layer has been removed, including the old route files, app entrypoint, and templates folder. The active UI entrypoint is `ui/main.py`, and the current user-facing pages live under `ui/pages/`.

The shared backend layer is still in place and is now the main foundation for the NiceGUI app. Core persistence and business logic live in `app/db.py`, `app/services/`, and `app/schemas.py`.

## What Is Working

- NiceGUI app shell and page routing are in place.
- Members page exists and supports member creation and deletion.
- Raid definitions page exists and supports create/delete flows.
- Weeks page exists and supports create/delete flows.
- Week detail page supports creating scheduled raids and deleting them.
- Confirmation flows exist for deleting items that already have dependent data.
- Search page exists and can search roster candidates and import the current top 6 characters into a selected member.
- Shared backend services are being reused by NiceGUI instead of duplicating logic in the UI layer.

## Important Constraints

The LostArk Bible search payload currently returns roster summary data, a matched character, total character count, and `top_characters`. It does not return the full roster character list.

That means the current “top 6 import” behavior is valid with the available API data, but “show all roster characters and choose which ones to import” is not currently possible without a second API endpoint. HTML scraping is intentionally off the table.

## Main Product Gaps

- Search/import UX still needs refinement so users understand exactly what will be imported.
- Character management is still limited to top 6 import behavior.
- Manual character editing or per-character add/update flows are not implemented yet.
- Assignment creation/editing UX still needs to be built out more fully.
- Visual consistency is improving, but forms and content density still need polish page by page.
- There is not yet a clear “member detail” workflow for ongoing roster maintenance.
- There is no automated test coverage protecting the current behavior.

## Recommended Next Product Steps

### 1. Finish the search/import flow

This is the most immediate workflow still in motion.

Recommended outcomes:
- make search result cards clearly communicate that importing will bring in the top 6 characters only
- show top character previews more clearly
- reduce noisy/ambiguous result presentation
- if possible, prefer one best exact roster match before showing multiple candidates

### 2. Add manual character management

Since a full-roster API is not currently available, manual maintenance is the right fallback.

Recommended outcomes:
- allow adding a character manually to a member
- allow editing imported character fields
- allow deactivating/removing characters without re-importing the whole member
- optionally support “fetch one character by name” if the existing search endpoint is enough for a single-character workflow

### 3. Build assignment management UX

The planner becomes much more useful once assignment flows are smooth.

Recommended outcomes:
- assign characters to scheduled raids from the week detail page
- view current assignments inline per raid
- support reassignment/removal without awkward refresh patterns

### 4. Improve search result selection logic

Search is still too literal and exposes too much raw API behavior.

Recommended outcomes:
- prefer exact `matched_character_name` hits
- if one exact match exists, treat it as the primary result
- if multiple exact matches exist, show a shortlist with stronger context
- make the “candidate roster” concept clearer to the user

## Coding Structure Improvements

### 1. Keep service boundaries sharper

A better split is now emerging:
- `members_service.py` should own member lifecycle and member-specific operations
- `search_service.py` should own roster search/import preparation
- `weeks_service.py` should own scheduling and assignment workflows
- `raids_service.py` should own raid definition behavior

Continue pushing toward “one service owns one domain” instead of mixing search/import/member responsibilities together.

### 2. Reduce tiny one-use helper functions

Several earlier flows became harder to follow because one process was split into too many very small helpers.

Preferred rule going forward:
- keep low-level reusable helpers when they are genuinely shared
- otherwise let one function own one complete workflow

Good example:
- `prepare_member_import(...)` is easier to follow than several tiny helpers chained together

### 3. Separate UI orchestration from persistence operations

NiceGUI page files should mostly do:
- gather widget values
- call one backend/service function
- refresh UI / notify user

They should avoid carrying business rules inline when that logic can live in services.

### 4. Create explicit single-item save/update paths

Some current backend paths still assume replace-all behavior.

Recommended future helpers:
- save one imported character to a member
- update one character row
- deactivate one character
- assign one character to one scheduled raid

These will make the next UX steps much easier to build cleanly.

### 5. Clean page-level consistency

The NiceGUI pages now mostly share shell/layout patterns, but some internal structures still drift.

Recommended direction:
- standardize form panels
- standardize list/detail sections
- standardize delete-confirm dialog wording
- standardize naming of helper callbacks like `create_*_from_form(...)`

## Technical Debt To Watch

- no tests yet for service workflows
- some UI pages still need cleanup from rapid iteration
- CSS has improved, but form styling is still sensitive and should be changed carefully
- route-layer cleanup is mostly done by removal, so the NiceGUI path should now become the only maintained UI path

## Suggested Implementation Order

1. Stabilize the search page and top 6 import UX.
2. Add manual character management for members.
3. Add assignment creation and editing on week detail.
4. Add test coverage for services before larger feature expansion.
5. Do a second-pass cleanup on naming, shared UI helpers, and dialog consistency.

## Summary

The project is in a good transition state: the old UI layer is gone, the NiceGUI app is real and functional, and the backend is becoming service-driven. The next gains should come from tightening the search/import experience, adding manual character management, and making the scheduling workflow easier to maintain.
