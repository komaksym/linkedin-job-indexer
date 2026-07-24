## Summary

- Add an HTTP-first daily LinkedIn job indexer using public guest HTML endpoints.
- Deduplicate jobs in SQLite, fetch full descriptions, filter deterministically, and export ranked CSV/JSON results.
- Add tests, CI, documentation, and a scheduled/manual GitHub Actions workflow.

## System flow

```mermaid
graph LR
    A[TOML searches] --> B[LinkedIn guest search HTML]
    B --> C[Unique job IDs]
    C --> D{Seen in SQLite?}
    D -- yes --> E[Skip]
    D -- no --> F[Fetch full description]
    F --> G[Reject / require / boost filters]
    G --> H[CSV + JSON]
    H --> I[Commit seen-state transaction]
```

## Validation

- `ruff check .`
- `mypy`
- `pytest`
- package wheel build
- bounded live guest-endpoint smoke test where network access is available

## Limitations

LinkedIn's guest endpoints are undocumented, best-effort, potentially incomplete, and may block cloud-hosted traffic. The program fails visibly on detected block pages instead of treating them as zero results.
