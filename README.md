# MyServers Tool

Server management UI. Logic lives in core/storage/connectors; UI stays thin. No secrets in repo—use keyring only.

## Setup

- Python 3.11+
- `pip install -r requirements.txt`

## Verify

```bash
python scripts/verify_setup.py
pytest -q
```
