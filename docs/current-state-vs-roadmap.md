# Lost Ark Scheduler

## Current State

The project is currently a roster import and member management app, not yet a full scheduling system.

What exists today:

- A FastAPI app with server-rendered HTML pages
- Local SQLite storage
- Member creation and deletion
- Character deletion
- Roster search through the LostArk Bible API
- Importing a selected roster into a member profile
- A members page that groups imported characters under each member

What this means in practice:

- The app can collect and store roster data
- It can show who belongs to the guild roster and which characters they have
- It does not yet support weekly planning, assignment, or availability collection

Current limitations:

- No real scheduling model yet
- No weekly planning view
- No availability submission flow
- No raid, group, or slot system
- No duplicate booking checks
- No support or DPS role awareness in scheduling
- No setup documentation or dependency list
- Limited validation and error handling

## What The Old Spreadsheet Was Actually Doing

The old spreadsheet was not just a list of characters. It was the weekly operating system for the guild.

The planner process looked like this:

- One person asks every member for weekly availability
- One person tracks each member's relevant characters
- One person creates the raids for the week
- One person assigns characters into raid groups
- One person tracks free spots, extras, substitutes, and hard-stop times

The spreadsheet therefore combined three jobs:

- Roster tracking
- Availability tracking
- Weekly raid planning

## Product Direction

The app should be shaped around replacing the weekly raid-sheet ritual, not just storing imported roster data.

The main user value should be:

- Collect availability faster
- See all usable characters in one place
- Build weekly raids and groups visually
- Track open spots and extras
- Reduce officer planning overhead

## Roadmap

### v0.1 - Guild Roster Base

Goal: make the current roster app reliable and ready to support scheduling features.

Scope:

- Fill in requirements and setup docs
- Improve validation and error handling
- Add timestamps properly
- Clarify member versus character data
- Add role-related fields such as support, DPS, flex, main, and alt

Outcome:

- Stable source of truth for members and characters

### v0.2 - Weekly Availability

Goal: replace the weekly "ask everyone manually" process.

Scope:

- Create week records
- Let members submit availability for selected days
- Support simple availability notes such as "after reset", "> 7:00pm", or "hard stop 10:30pm"
- Give officers a weekly availability table

Outcome:

- Officers no longer need to gather availability manually in chat

### v0.3 - Raid Planning Board

Goal: replace the spreadsheet's scheduling section.

Scope:

- Create raids for a week
- Store raid type, day, and start time
- Create multiple groups per raid
- Assign characters into groups
- Track extras and open spots
- Show support versus DPS gaps

Outcome:

- The guild can build the weekly plan inside the app

### v0.4 - Scheduling Intelligence

Goal: reduce manual planner effort.

Scope:

- Filter eligible characters for each raid
- Warn about duplicate bookings
- Warn about missing support coverage
- Suggest likely fill candidates based on availability and roster data
- Keep per-raid notes

Outcome:

- The app becomes an assistant, not just a digital whiteboard

### v0.5 - Guild Workflow

Goal: make the tool sustainable for regular use.

Scope:

- Member self-service availability submission
- Officer-only planning controls
- Read-only weekly board for everyone else
- Weekly history
- Reuse last week's structure as a template

Outcome:

- The scheduling workflow becomes repeatable and easier to maintain

## Recommended Build Order

1. Members and characters
2. Weekly availability
3. Weekly planner page
4. Raid and group assignments
5. Open spots and duplicate-conflict warnings
6. Member self-service and history

## Suggested Core Data Model

- members
- characters
- weeks
- availability_entries
- raids
- raid_groups
- assignments

## Summary

Current state:

- A useful roster import prototype
- Good starting point for guild data
- Not yet a scheduling product

Target state:

- A weekly planning tool for officers
- A structured availability workflow for members
- A raid assignment board that replaces the current spreadsheet
