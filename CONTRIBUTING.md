# Contributing Adapters

## Adapter Requirements

1. Subclass `BaseMosoroAdapter` from `mosoro-core`
2. Implement all required methods: `connect()`, `disconnect()`, `poll_status()`, `send_command()`
3. Map vendor-specific status values to MosoroMessage status enum
4. Include a YAML config template
5. Include a README with setup instructions
6. Include tests that validate against the MosoroMessage schema

## Directory Structure

```
adapters/{vendor}/
├── __init__.py
├── {vendor}_adapter.py    ← Your adapter implementation
├── {vendor}.yaml          ← Default config template
├── README.md              ← Setup instructions
└── tests/
    └── test_{vendor}.py   ← Adapter-specific tests
```

## Submission Process

1. Fork this repository
2. Create your adapter in `adapters/{vendor}/`
3. Run the shared test harness: `pytest tests/test_adapter_contract.py`
4. Submit a Pull Request
5. A maintainer will review and merge
