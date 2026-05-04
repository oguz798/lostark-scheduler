# Lost Ark Scheduler

Lost Ark Scheduler is a small NiceGUI app for importing guild roster data and managing members locally as the foundation for a weekly raid planner.

## Current scope

Right now the app can:

- create members
- search rosters through the LostArk Bible API
- import top characters into a member
- browse members and imported characters
- create raid definitions
- create weeks and scheduled raids
- assign characters to scheduled raids
- delete members, raid definitions, weeks, and scheduled raids

## Tech stack

- Python 3.12+
- NiceGUI
- SQLite
- httpx

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the app

```powershell
python -m ui.main
```

Then open the local URL shown in the terminal.

## Project structure

- `ui/main.py`: NiceGUI entrypoint
- `ui/pages/`: NiceGUI pages
- `ui/components/`: shared UI layout/components
- `ui/styles/`: NiceGUI-specific CSS
- `app/db.py`: SQLite setup and persistence helpers
- `app/schemas.py`: dataclasses for roster search results
- `app/services/`: backend service layer and LostArk Bible integration
- `static/`: legacy static assets still available if needed
- `docs/`: planning and roadmap documents

## Notes

- The local database file is `lostark_scheduler.sqlite3`.
- Search and import depend on the external LostArk Bible API being reachable.
