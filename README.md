# MyServers Tool v2

Server management UI. Business logic in `myservers/core`; storage in `myservers/storage`; UI thin. No secrets in repo—use keyring only.

## v2 layout

- **myservers/app.py** – entrypoint (PySide6 + MainWindow from `myservers.ui.main_window`)
- **myservers/ui/main_window.py** – main window
- **myservers/storage/json_store.py** – JSON store (legacy-compatible)
- **tests/test_json_store.py** – JsonStore tests
- **legacy/** – previous project (main.py, ViewController.py, support/, etc.); not used by v2.

## Setup

- Python 3.11+
- `pip install -r requirements.txt`

## Verify

```bash
python scripts/verify_setup.py
pytest -q
```

## Run v2 app

```bash
python -m myservers.app
```
