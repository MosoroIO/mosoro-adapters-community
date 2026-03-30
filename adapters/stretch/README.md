# Mosoro Stretch Adapter

Adapter for the **Boston Dynamics Stretch** mobile manipulator. Connects to the
robot's ROS 2 stack via the [rosbridge](https://github.com/RobotWebTools/rosbridge_suite)
WebSocket protocol using the [`roslibpy`](https://pypi.org/project/roslibpy/) Python library.

## What It Does

The Stretch adapter translates between Mosoro's normalized message format and
the Stretch robot's native ROS 2 topics. It:

- Subscribes to joint-state, battery, odometry, and diagnostics topics to build
  a unified status payload.
- Publishes velocity, navigation, trajectory, and gripper commands received from
  the Mosoro gateway.
- Reports the robot's position, battery level, health, and task status in the
  standard `MosoroMessage` schema.

## Prerequisites

| Requirement | Details |
|---|---|
| **Python** | 3.10+ |
| **ROS 2** | Humble or later, running on the Stretch robot |
| **rosbridge_server** | Part of `rosbridge_suite`; must be running on the Stretch |
| **roslibpy** | Python client library for rosbridge (installed on the Mosoro host) |
| **Mosoro Core** | `mosoro-core` with `BaseMosoroAdapter` available |

## Installation

### 1. Install roslibpy

`roslibpy` is the Python library that communicates with ROS / ROS 2 over the
rosbridge WebSocket protocol. Install it on the machine running the Mosoro
edge agent (not necessarily on the Stretch itself):

```bash
pip install roslibpy
```

Or, if you are using the community adapters package:

```bash
pip install mosoro-adapters-community[stretch]
```

### 2. Start rosbridge on the Stretch robot

On the Stretch robot (which runs ROS 2), launch the rosbridge WebSocket server:

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

This starts a WebSocket server on **port 9090** by default. Verify it is
running:

```bash
# From any machine on the same network:
curl -s http://<stretch_ip>:9090 || echo "rosbridge not reachable"
```

> **Tip:** To start rosbridge automatically on boot, add it to a systemd
> service or your Stretch's launch configuration.

### 3. Install the adapter package

If you haven't already installed the community adapters:

```bash
pip install mosoro-adapters-community
```

## Configuration

The adapter is configured via a YAML file. See
[`stretch.yaml`](stretch.yaml) for the full reference.

Key settings:

```yaml
robot_id: "stretch-001"
vendor: "stretch"

# rosbridge WebSocket connection
rosbridge_host: "192.168.1.101"   # IP address of the Stretch robot
rosbridge_port: 9090              # Default rosbridge WebSocket port

# ROS 2 topic names (adjust for your namespace)
topic_joint_states: "/stretch/joint_states"
topic_battery: "/battery_state"
topic_odom: "/odom"
topic_diagnostics: "/diagnostics_agg"
topic_cmd_vel: "/stretch/cmd_vel"
topic_navigate: "/stretch/navigate_to_pose"
topic_joint_trajectory: "/stretch/joint_trajectory"
topic_gripper: "/stretch/gripper_command"

# MQTT connection to the Mosoro broker
mqtt_broker: "mosquitto"
mqtt_port: 8883
mqtt_use_tls: true

poll_interval: 4.0
log_level: "INFO"
```

## Running the Adapter

### Standalone

```bash
python -m agents.core.agent agents/config/stretch.yaml
```

### With Docker (production)

The adapter runs as a container in the Mosoro stack. See
`mosoro-core/docker/docker-compose.prod.yml` for the `agent-stretch` service
definition. Environment variables (`MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, etc.)
are set in the compose file.

```bash
docker compose -f mosoro-core/docker/docker-compose.prod.yml up agent-stretch
```

## Architecture

```
┌──────────────┐  WebSocket (ws://stretch:9090)  ┌──────────────────┐
│  Mosoro Edge  │ ◄──────────────────────────────► │  rosbridge_server │
│  Agent        │    roslibpy                      │  (on Stretch)     │
│  + Stretch    │                                  │                   │
│    Adapter    │                                  │  ROS 2 topics     │
└──────┬───────┘                                  └──────────────────┘
       │ MQTT (TLS)
       ▼
┌──────────────┐
│  Mosquitto   │
│  Broker      │
└──────────────┘
```

## Troubleshooting

### "Connection refused" when connecting to rosbridge

- Verify `rosbridge_server` is running on the Stretch:
  ```bash
  ros2 node list | grep rosbridge
  ```
- Check the Stretch's firewall allows connections on port 9090.
- Ensure `rosbridge_host` in `stretch.yaml` matches the Stretch's IP address.

### "ModuleNotFoundError: No module named 'roslibpy'"

Install the dependency:
```bash
pip install roslibpy
```

### Adapter connects but receives no data

- Confirm ROS 2 topics are publishing on the Stretch:
  ```bash
  ros2 topic list
  ros2 topic echo /stretch/joint_states
  ```
- Verify the topic names in `stretch.yaml` match the actual ROS 2 topic names
  on your Stretch (namespaces may differ).

### Battery or position data is missing

- The Stretch may not publish `/battery_state` or `/odom` until the robot is
  fully initialized. Wait for the robot to complete its startup sequence.
- Check `topic_battery` and `topic_odom` in the YAML config.

### TLS / MQTT connection issues

- See the main [Mosoro Core README](../../../mosoro-core/README.md) for MQTT TLS
  configuration and certificate setup.
- For development without TLS, set `mqtt_port: 1883` and `mqtt_use_tls: false`
  in `stretch.yaml`.

## References

- [roslibpy documentation](https://roslibpy.readthedocs.io/)
- [rosbridge_suite (GitHub)](https://github.com/RobotWebTools/rosbridge_suite)
- [Boston Dynamics Stretch documentation](https://docs.hello-robot.com/)
- [Mosoro Adapter Development Guide](../../_template/README.md)
