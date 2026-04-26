# VocalAnnotate 

A voice-first annotation companion for students reading physical books.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## How to Use

1. **Add a book** — type the title in the sidebar and press Enter or click `+`
2. **Select a book** — click it in the sidebar
3. **Annotate by voice** — click the 🎤 button, then say:
   - `"Page 47, symbolism of the green light"`
   - `"Page 103, quote — old sport repetition"`
   - `"Pg 22 foreshadowing"`
4. **Annotate by typing** — use the text box at the bottom with the same format
5. **View notes** — sorted by page number, automatically

## Supported Voice Formats

| You say | Parsed as |
|---|---|
| `Page 42, symbolism of hope` | Page 42 |
| `page 103 quote colon old sport` | Page 103, note: "quote: old sport" |
| `Pg 22 foreshadowing` | Page 22 |
| `Page seventy six character shift` | Page 76 |
| `Page 12 comma motif of darkness` | Page 12 |

## Voice Requirements

- Requires internet (uses Google Web Speech API)
- For offline use, replace `voice/recorder.py` with WisprFlow local integration

## Project Structure

```
vocalannotate/
├── main.py          # Entry point
├── ui/app.py        # Main application UI
├── db/database.py   # SQLite models + CRUD
├── voice/
│   ├── recorder.py  # Mic capture + speech-to-text
│   └── parser.py    # Page number and annotation extraction
└── requirements.txt
```

## Data Storage

All notes saved to `vocalannotate.db` (SQLite) in the project folder.
