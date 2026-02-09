# Agent Instructions

## Overview
This project is a Telegram AI Agent with Memory and Reporting capabilities.

## Architecture
- **Backend:** Python (FastAPI, Telethon, Google Gemini).
- **Database:** SQLite (SQLModel).
- **Services:** `LearningService`, `ConversationService`, `ReportingService`, `AIService`.

## Key Files
- `backend/services/ai.py`: Handles LLM interactions.
- `backend/services/learning.py`: Ingests history and extracts facts.
- `backend/settings.py`: Configuration.

## Testing
Always run tests before submitting changes.
`make test` or `python -m pytest`

## Coding Standards
- Use `black` for formatting.
- Use `flake8` for linting.
- Add type hints to all functions.
- Handle exceptions gracefully.

## Best Practices
- **Memory:** When modifying `AIService`, ensure prompts are updated in `backend/prompts.py`.
- **Learning:** `LearningService` uses `MIN_MESSAGE_LENGTH_FOR_LEARNING` to filter noise.
- **Reporting:** Daily reports are scheduled in `backend/server.py` and handled by `ReportingService`.
