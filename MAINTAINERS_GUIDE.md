# Maintainer's guide

This file has been written exclusively by Codex - use with caution.

## File structure

| Area | File |
| --- | --- |
| App startup, navigation and nickname UI | `streamlit_app.py` |
| Data, paper, logging, plot and leaderboard pages | `ccsdb/pages.py` |
| Database schema and all reads/writes | `ccsdb/database.py` |
| Sign-in and approved-email checks | `ccsdb/auth.py` |
| Runtime settings and secrets access | `ccsdb/config.py` |
| Plotly figure and interactive download | `ccsdb/plotting.py` |
| DOI normalisation and validation | `ccsdb/doi.py` |
| Initial paper catalogue | `data/papers.json` |
| Streamlit visual/server settings | `.streamlit/config.toml` |
| Example authentication and database settings | `.streamlit/secrets.toml.example` |
| Automated checks | `tests/test_database.py` |

## Data model

```text
papers
  └── entries
        └── measurements

users ── entries
users ── measurements
papers ── assignments
```

The catalogue seeder creates papers only. It never creates accounts or CCS
records. A user row is created after a person authenticates with an email in the
allowlist. Every entry and CCS value is attributed to that user.

`measurements.measurement_type` is either `charge_state` or `global`. A global
measurement can optionally store a minimum and maximum charge state.

## Production rules

- Keep the viewer list and `[access].approved_emails` aligned.
- Use managed PostgreSQL in production; SQLite is only for local development.
- Store identity-provider keys, database credentials, and email allowlists in
  Streamlit Secrets, never in Git.
- Run the unit tests before each deployment.
