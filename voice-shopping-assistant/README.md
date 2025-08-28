# Voice Command Shopping Assistant (Flask + HTML + CSS)

A minimalist voice-driven shopping list manager with smart suggestions.

## Features
- Voice input in the browser (Web Speech API) with language selector
- NLP (rule-based) to parse intents like add/remove/search and extract quantity & item
- Shopping list CRUD with auto-categories and quantities
- Smart suggestions (history-based frequency, seasonal items, simple substitutes)
- Voice-activated search across a sample product catalog with filters (price/brand)
- Clean UI with real-time transcription and confirmations

## Tech
- **Backend:** Python (Flask), SQLite
- **Frontend:** HTML, CSS, minimal JavaScript for voice capture and API calls
- **Data:** JSON catalog in `data/products.json`

## Run locally
```bash
# 1) (Optional) create & activate venv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Start the app
python app.py

# 4) Open
# visit http://127.0.0.1:5000
```

## Project structure
```
voice-shopping-assistant/
├─ app.py
├─ requirements.txt
├─ README.md
├─ data/
│  └─ products.json
├─ templates/
│  └─ index.html
└─ static/
   ├─ style.css
   └─ app.js
```

## Notes
- Web Speech API is supported in Chromium-based browsers. If voice doesn't work, you can type commands into the input box.
- This is a simple, self-contained implementation suited for a technical assessment.