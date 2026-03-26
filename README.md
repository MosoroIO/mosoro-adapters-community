# Mosoro Community Adapters

Community-contributed robot adapters for [Mosoro Core](https://github.com/mosoroio/mosoro-core).

## Available Adapters

| Adapter | Vendor | Status | Connection |
|---|---|---|---|
| [Fetch](adapters/fetch/) | Fetch Robotics (Zebra) | ✅ Production | REST API |
| [Geekplus](adapters/geekplus/) | Geekplus / Seer | ✅ Production | REST API |
| [Locus](adapters/locus/) | Locus Robotics | ✅ Production | REST API |
| [MiR](adapters/mir/) | Mobile Industrial Robots | ✅ Production | REST API (Basic Auth) |
| [Stretch](adapters/stretch/) | Boston Dynamics | 🚧 Placeholder | ROS 2 Bridge |

## Installation

```bash
pip install mosoro-adapters-community
```

This automatically registers all adapters with Mosoro Core via entry points. The edge agent will discover them at runtime — no manual configuration needed.

## Usage

Once installed, configure your agent with the vendor name:

```yaml
# config.yaml
robot_id: "fetch-001"
vendor: "fetch"
api_base_url: "http://192.168.1.210:8080"
api_key: "your-api-key"
```

The agent will automatically discover and load the correct adapter.

## Creating a New Adapter

1. Copy the template: `cp -r adapters/_template adapters/my_vendor`
2. Implement `_fetch_robot_status()` and `send_command()`
3. Add your adapter to `pyproject.toml` entry points
4. Add tests
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

## Development

```bash
# Clone and install in development mode
git clone https://github.com/mosoroio/mosoro-adapters-community.git
cd mosoro-adapters-community
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
