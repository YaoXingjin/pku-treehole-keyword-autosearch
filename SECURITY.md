# Security Policy

## Sensitive Data

Do not commit:

- `config_private.py`
- PKU account names or passwords
- MeoW nicknames if you consider them private
- cookies or session files
- treehole state files
- logs
- raw search result dumps containing treehole content

Before publishing a fork or release, run a local scan for identifiers, account
numbers, passwords, hostnames, IP addresses, SSH paths, nicknames, logs, and
JSON state files.

## Reporting

If you find a security issue, open a private report if the hosting platform
supports it. Otherwise, contact the maintainer without including live
credentials or session data in a public issue.
