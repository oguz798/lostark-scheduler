# Lost Ark Scheduler

Lost Ark Scheduler is a small FastAPI app for importing guild roster data and managing members locally as the foundation for a weekly raid planner.

## Current scope

Right now the app can:

- create members
- search rosters through the LostArk Bible API
- import top characters into a member
- browse members and imported characters
- delete members and characters

The next planned step is weekly availability and raid planning.

## Tech stack

- Python 3.12+
- FastAPI
- Jinja2 templates
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
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000

## Project structure

- `app/main.py`: FastAPI routes and page rendering
- `app/db.py`: SQLite setup and persistence helpers
- `app/schemas.py`: dataclasses for roster search results
- `app/services/lostark_bible.py`: external roster API integration
- `templates/`: server-rendered HTML templates
- `static/`: CSS
- `docs/`: planning and roadmap documents

## Notes

- The local database file is `lostark_scheduler.sqlite3`.
- Search and import depend on the external LostArk Bible API being reachable.
