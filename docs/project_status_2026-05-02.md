Lostark Scheduler - End of Day Recap
Date: 2026-05-02

What we finished today
- Continued week detail assignment flow work in NiceGUI.
- Implemented/verified drag-and-drop assignment flow scaffolding.
- Fixed role source in drag payload to use combat_role.
- Added party split logic for 8-player raids (slots 1-4 / 5-8).
- Added check_party_add concept (3 DPS + 1 SUP per party).
- Added filters in assignment view (role + show assigned).
- Started grouping character pool by member_id.
- Deferred raid summary display to a cleaner separate page later.

Important decisions
- Keep learning-first, step-by-step workflow.
- Favor readability over over-abstract helpers.
- Keep DB naming aligned with existing schema.
- Defer UX polish; prioritize core scheduling logic.

Current status
- check_party_add wired into drop flow.
- Grouped pool data exists; grouped render still to finish.
- Weekly raid rule snippet prepared, pending full integration.

Next steps
1) Finish grouped pool rendering (collapse by member, ilvl desc).
2) Add weekly constraints (max 3 different raids, no same raid def).
3) Harden party validation (4-man no party2 slot path).
4) Verify local refresh behavior after assignment.
5) Revisit summary in dedicated view later.

Quick checks next session
- Test 4-man and 8-man assignment flows.
- Test role filter and show_assigned.
- Test duplicate + weekly limit rules.
