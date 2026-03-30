# Fetch Robotics (Zebra) Adapter

Mosoro adapter for [Fetch Robotics](https://www.zebra.com/us/en/solutions/intelligent-automation/fetch-robotics.html) (now Zebra Technologies) AMRs.

## Supported Robots

- Fetch CartConnect
- Fetch RollerTop
- Fetch HMIShelf
- Other FetchCore-managed robots

## Connection

This adapter connects via the **FetchCore REST API** using Bearer token authentication.

## Configuration

Copy `fetch.yaml` to your agent config directory and update:

```yaml
robot_id: "fetch-001"
vendor: "fetch"
api_base_url: "http://YOUR_FETCH_HOST:8080"
api_key: "your-fetch-api-key-here"
api_version: "v1"
```

## Status Mapping

| Fetch State | Mosoro Status |
|---|---|
| IDLE | idle |
| NAVIGATING | moving |
| EXECUTING | working |
| DOCKING | moving |
| CHARGING | charging |
| ERROR | error |
| PAUSED | idle |
| MANUAL | working |
| OFFLINE | offline |

## Commands

| Mosoro Command | Fetch API Call |
|---|---|
| `move_to` | `POST /api/v1/tasks` |
| `pause` | `PUT /api/v1/robots/{id}/action` |
| `resume` | `PUT /api/v1/robots/{id}/action` |
| `dock` | `PUT /api/v1/robots/{id}/action` |
| `undock` | `PUT /api/v1/robots/{id}/action` |
