# Mosoro Community Adapters

Community-contributed robot adapters for [Mosoro Core](https://github.com/mosoro/mosoro-core).

## Available Adapters

_No community adapters yet. Be the first to contribute!_

## Creating an Adapter

1. Copy the `adapters/_template/` directory
2. Rename it to `adapters/{your_vendor}/`
3. Implement the adapter by subclassing `BaseMosoroAdapter`
4. Add tests
5. Submit a PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Installation

```bash
# Install a specific adapter
pip install mosoro-adapter-{vendor}

# Or copy adapter files directly into your mosoro-core agents/adapters/ directory
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
