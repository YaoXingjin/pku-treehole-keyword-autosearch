# Contributing

Thanks for improving this project.

## Development

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m py_compile client.py meow_push.py search_keyword.py scripts/its_network_login.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m py_compile client.py meow_push.py search_keyword.py scripts\its_network_login.py
```

## Privacy

Keep examples generic. Do not include real PKU accounts, passwords, MeoW
nicknames, SSH private key paths, IP addresses that identify a personal
instance, cookies, logs, state files, or raw treehole search result dumps.

## References

The PKU Treehole login and search request implementation is based on ideas
from [SunVapor/pku-treehole-search-agent](https://github.com/SunVapor/pku-treehole-search-agent).
