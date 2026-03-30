# Copyright 2026 Mosoro Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
Mosoro Adapter for Boston Dynamics Stretch
==========================================

Stretch uses ROS 2 for control and telemetry. This adapter connects to the
robot's ``rosbridge_server`` WebSocket interface via the ``roslibpy`` library,
subscribing to standard ROS 2 topics for status data and publishing commands
to action/trajectory topics.

External dependency (install separately):
    pip install roslibpy

ROS 2 topics used:
    Subscribe:
        /stretch/joint_states    (sensor_msgs/JointState)   — arm & gripper
        /battery_state           (sensor_msgs/BatteryState)  — battery level
        /odom                    (nav_msgs/Odometry)          — position
        /diagnostics_agg         (diagnostic_msgs/DiagnosticArray) — health
    Publish / Action:
        /stretch/cmd_vel         (geometry_msgs/Twist)        — base velocity
        /stretch/navigate_to_pose (geometry_msgs/PoseStamped) — navigation goal
        /stretch/joint_trajectory (trajectory_msgs/JointTrajectory) — arm cmds
        /stretch/gripper_command (control_msgs/GripperCommand) — gripper
"""

import asyncio
import math
import threading
from typing import Any, Dict, List, Optional

try:
    import roslibpy
except ImportError:
    roslibpy = None  # type: ignore[assignment]  # Deferred: only needed at runtime

from mosoro_core.base_adapter import BaseMosoroAdapter


class StretchAdapter(BaseMosoroAdapter):
    """Adapter for Boston Dynamics Stretch mobile manipulator via rosbridge."""

    vendor_name = "stretch"

    # Mosoro-standard status values
    _STATUS_IDLE = "idle"
    _STATUS_MOVING = "moving"
    _STATUS_WORKING = "working"
    _STATUS_CHARGING = "charging"
    _STATUS_ERROR = "error"
    _STATUS_OFFLINE = "offline"

    def __init__(self, robot_id: str, config: Dict[str, Any]) -> None:
        super().__init__(robot_id, config)

        # rosbridge connection parameters
        self.rosbridge_host: str = config.get("rosbridge_host", "localhost")
        self.rosbridge_port: int = int(config.get("rosbridge_port", 9090))

        # Topic names (configurable for different Stretch deployments)
        self.topic_joint_states: str = config.get("topic_joint_states", "/stretch/joint_states")
        self.topic_battery: str = config.get("topic_battery", "/battery_state")
        self.topic_odom: str = config.get("topic_odom", "/odom")
        self.topic_diagnostics: str = config.get("topic_diagnostics", "/diagnostics_agg")
        self.topic_cmd_vel: str = config.get("topic_cmd_vel", "/stretch/cmd_vel")
        self.topic_navigate: str = config.get("topic_navigate", "/stretch/navigate_to_pose")
        self.topic_joint_trajectory: str = config.get(
            "topic_joint_trajectory", "/stretch/joint_trajectory"
        )
        self.topic_gripper: str = config.get("topic_gripper", "/stretch/gripper_command")

        # roslibpy client and subscribers
        self._ros: Any = None
        self._subscribers: List[Any] = []
        self._ros_thread: Optional[threading.Thread] = None

        # Cached latest data from ROS subscriptions (thread-safe via lock)
        self._lock = threading.Lock()
        self._joint_state: Dict[str, Any] = {}
        self._battery_state: Dict[str, Any] = {}
        self._odom_state: Dict[str, Any] = {}
        self._diagnostics: List[Dict[str, Any]] = []
        self._robot_status: str = self._STATUS_IDLE

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish WebSocket connection to the Stretch rosbridge server."""
        if roslibpy is None:
            raise ImportError(
                "roslibpy is required for the Stretch adapter. "
                "Install it with: pip install roslibpy"
            )
        try:
            self._ros = roslibpy.Ros(host=self.rosbridge_host, port=self.rosbridge_port)

            # roslibpy uses a blocking event loop; run it in a background thread
            self._ros_thread = threading.Thread(target=self._run_ros_connection, daemon=True)
            self._ros_thread.start()

            # Wait for connection (with timeout)
            timeout_seconds = int(self.config.get("api_timeout", 12))
            for _ in range(timeout_seconds * 10):
                if self._ros.is_connected:
                    break
                await asyncio.sleep(0.1)

            if not self._ros.is_connected:
                self.logger.error(
                    f"Timed out connecting to rosbridge at "
                    f"ws://{self.rosbridge_host}:{self.rosbridge_port}"
                )
                self.connected = False
                return False

            self._subscribe_topics()
            self.connected = True
            self.logger.info(
                f"Stretch adapter {self.robot_id} connected to rosbridge at "
                f"ws://{self.rosbridge_host}:{self.rosbridge_port}"
            )
            return True

        except Exception as exc:
            self.logger.error(f"Failed to connect to rosbridge: {exc}")
            self.connected = False
            return False

    def _run_ros_connection(self) -> None:
        """Run the roslibpy event loop in a background thread."""
        try:
            self._ros.run()
        except Exception as exc:
            self.logger.error(f"rosbridge connection loop error: {exc}")

    async def disconnect(self) -> None:
        """Disconnect from the rosbridge server and clean up subscriptions."""
        try:
            for subscriber in self._subscribers:
                try:
                    subscriber.unsubscribe()
                except Exception:
                    pass
            self._subscribers.clear()

            if self._ros and self._ros.is_connected:
                self._ros.terminate()

        except Exception as exc:
            self.logger.warning(f"Error during rosbridge disconnect: {exc}")
        finally:
            self.connected = False
            self.logger.info(f"Stretch adapter {self.robot_id} disconnected")

    # ------------------------------------------------------------------
    # ROS 2 topic subscriptions
    # ------------------------------------------------------------------

    def _subscribe_topics(self) -> None:
        """Subscribe to all relevant ROS 2 topics for status telemetry."""
        self._subscribe(
            self.topic_joint_states,
            "sensor_msgs/JointState",
            self._on_joint_state,
        )
        self._subscribe(
            self.topic_battery,
            "sensor_msgs/BatteryState",
            self._on_battery_state,
        )
        self._subscribe(
            self.topic_odom,
            "nav_msgs/Odometry",
            self._on_odom,
        )
        self._subscribe(
            self.topic_diagnostics,
            "diagnostic_msgs/DiagnosticArray",
            self._on_diagnostics,
        )

    def _subscribe(self, topic_name: str, msg_type: str, callback: Any) -> None:
        """Create a roslibpy subscriber and register the callback."""
        topic = roslibpy.Topic(self._ros, topic_name, msg_type)
        topic.subscribe(callback)
        self._subscribers.append(topic)
        self.logger.debug(f"Subscribed to {topic_name} ({msg_type})")

    # ------------------------------------------------------------------
    # Subscription callbacks (run on roslibpy's background thread)
    # ------------------------------------------------------------------

    def _on_joint_state(self, message: Dict[str, Any]) -> None:
        """Handle incoming JointState messages."""
        with self._lock:
            names: List[str] = message.get("name", [])
            positions: List[float] = message.get("position", [])
            velocities: List[float] = message.get("velocity", [])
            efforts: List[float] = message.get("effort", [])

            joints: Dict[str, Dict[str, float]] = {}
            for i, name in enumerate(names):
                joints[name] = {
                    "position": positions[i] if i < len(positions) else 0.0,
                    "velocity": velocities[i] if i < len(velocities) else 0.0,
                    "effort": efforts[i] if i < len(efforts) else 0.0,
                }
            self._joint_state = joints

            # Infer working status from arm/gripper motion
            is_arm_moving = any(
                abs(j.get("velocity", 0.0)) > 0.01
                for name, j in joints.items()
                if "arm" in name or "gripper" in name or "wrist" in name
            )
            if is_arm_moving:
                self._robot_status = self._STATUS_WORKING

    def _on_battery_state(self, message: Dict[str, Any]) -> None:
        """Handle incoming BatteryState messages."""
        with self._lock:
            self._battery_state = {
                "voltage": message.get("voltage", 0.0),
                "current": message.get("current", 0.0),
                "percentage": message.get("percentage", 0.0) * 100.0,
                "charge": message.get("charge", 0.0),
                "capacity": message.get("capacity", 0.0),
                "present": message.get("present", True),
                "power_supply_status": message.get("power_supply_status", 0),
            }

            # Detect charging from power_supply_status
            # BatteryState constants: 0=UNKNOWN, 1=CHARGING, 2=DISCHARGING,
            #                         3=NOT_CHARGING, 4=FULL
            pss = message.get("power_supply_status", 0)
            if pss == 1:
                self._robot_status = self._STATUS_CHARGING

    def _on_odom(self, message: Dict[str, Any]) -> None:
        """Handle incoming Odometry messages."""
        with self._lock:
            pose = message.get("pose", {}).get("pose", {})
            position = pose.get("position", {})
            orientation = pose.get("orientation", {})
            twist = message.get("twist", {}).get("twist", {})
            linear_vel = twist.get("linear", {})
            angular_vel = twist.get("angular", {})

            self._odom_state = {
                "x": position.get("x", 0.0),
                "y": position.get("y", 0.0),
                "z": position.get("z", 0.0),
                "orientation": orientation,
                "heading": self._quaternion_to_yaw(orientation),
                "linear_velocity": linear_vel,
                "angular_velocity": angular_vel,
            }

            # Infer moving status from base velocity
            linear_speed = math.sqrt(linear_vel.get("x", 0.0) ** 2 + linear_vel.get("y", 0.0) ** 2)
            if linear_speed > 0.05:
                self._robot_status = self._STATUS_MOVING
            elif self._robot_status == self._STATUS_MOVING and linear_speed < 0.01:
                self._robot_status = self._STATUS_IDLE

    def _on_diagnostics(self, message: Dict[str, Any]) -> None:
        """Handle incoming DiagnosticArray messages."""
        with self._lock:
            statuses = message.get("status", [])
            self._diagnostics = statuses

            # Check for error-level diagnostics
            for diag in statuses:
                level = diag.get("level", 0)
                # DiagnosticStatus levels: 0=OK, 1=WARN, 2=ERROR, 3=STALE
                if level >= 2:
                    self._robot_status = self._STATUS_ERROR
                    break

    # ------------------------------------------------------------------
    # Status fetching (called by BaseMosoroAdapter polling loop)
    # ------------------------------------------------------------------

    async def _fetch_robot_status(self) -> Dict[str, Any]:
        """Build normalized Mosoro status from cached ROS 2 topic data."""
        if not self._ros or not self._ros.is_connected:
            self.logger.error("rosbridge not connected — cannot fetch status")
            raise ConnectionError("rosbridge WebSocket is not connected")

        with self._lock:
            battery_pct = self._battery_state.get("percentage", 0.0)
            odom = self._odom_state
            joints = self._joint_state

            # Extract arm-specific joint data for vendor_specific
            arm_extension = joints.get("joint_arm_l0", {}).get("position", 0.0)
            wrist_yaw = joints.get("joint_wrist_yaw", {}).get("position", 0.0)
            gripper_pos = joints.get("joint_gripper_finger_left", {}).get("position", 0.0)
            lift_pos = joints.get("joint_lift", {}).get("position", 0.0)
            head_pan = joints.get("joint_head_pan", {}).get("position", 0.0)
            head_tilt = joints.get("joint_head_tilt", {}).get("position", 0.0)

            # Determine gripper state from finger position
            gripper_state = "open" if gripper_pos > 0.02 else "closed"

            return {
                "position": {
                    "x": odom.get("x", 0.0),
                    "y": odom.get("y", 0.0),
                    "z": odom.get("z", 0.0),
                    "theta": odom.get("heading", 0.0),
                    "map_id": self.config.get("map_id", "default_map"),
                },
                "battery": round(battery_pct, 1),
                "status": self._robot_status,
                "current_task": None,  # Task tracking managed by Mosoro Core
                "health": self._assess_health(),
                "errors": self._collect_errors(),
                "vendor_specific": {
                    "arm_extension": round(arm_extension, 4),
                    "lift_position": round(lift_pos, 4),
                    "wrist_yaw": round(wrist_yaw, 4),
                    "gripper_state": gripper_state,
                    "gripper_position": round(gripper_pos, 4),
                    "head_pan": round(head_pan, 4),
                    "head_tilt": round(head_tilt, 4),
                    "base_velocity": {
                        "linear_x": odom.get("linear_velocity", {}).get("x", 0.0),
                        "angular_z": odom.get("angular_velocity", {}).get("z", 0.0),
                    },
                    "battery_voltage": self._battery_state.get("voltage", 0.0),
                    "battery_current": self._battery_state.get("current", 0.0),
                    "joint_names": list(joints.keys()),
                },
            }

    def _assess_health(self) -> str:
        """Assess overall robot health from diagnostics data."""
        max_level = 0
        for diag in self._diagnostics:
            level = diag.get("level", 0)
            if level > max_level:
                max_level = level

        if max_level >= 2:
            return "error"
        if max_level == 1:
            return "warning"
        return "good"

    def _collect_errors(self) -> List[Dict[str, str]]:
        """Collect error/warning messages from diagnostics."""
        errors: List[Dict[str, str]] = []
        for diag in self._diagnostics:
            level = diag.get("level", 0)
            if level >= 1:
                errors.append(
                    {
                        "code": diag.get("name", "unknown"),
                        "message": diag.get("message", ""),
                    }
                )
        return errors

    # ------------------------------------------------------------------
    # Command sending
    # ------------------------------------------------------------------

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send a command to the Stretch robot via ROS 2 topics.

        Supported actions:
            move_to   — Navigate to a pose (x, y, theta)
            stop      — Stop all motion (zero velocity)
            pick      — Execute arm pick sequence (extend + close gripper)
            place     — Execute arm place sequence (extend + open gripper)
            home      — Send all joints to home/stow position
            arm_move  — Move arm to specified joint positions
            gripper   — Open or close the gripper
        """
        if not self._ros or not self._ros.is_connected:
            self.logger.error("rosbridge not connected — cannot send command")
            return False

        action = command.get("action")
        self.logger.info(f"Sending '{action}' command to Stretch {self.robot_id}")

        try:
            if action == "move_to":
                return self._publish_navigate_goal(command)

            elif action == "stop":
                return self._publish_stop()

            elif action == "pick":
                return self._publish_pick_sequence(command)

            elif action == "place":
                return self._publish_place_sequence(command)

            elif action == "home":
                return self._publish_home_position()

            elif action == "arm_move":
                return self._publish_joint_trajectory(command)

            elif action == "gripper":
                return self._publish_gripper_command(command)

            self.logger.warning(f"Unsupported command action: {action}")
            return False

        except Exception as exc:
            self.logger.error(f"Failed to send command to Stretch: {exc}")
            return False

    # ------------------------------------------------------------------
    # Command publishers
    # ------------------------------------------------------------------

    def _publish_navigate_goal(self, command: Dict[str, Any]) -> bool:
        """Publish a PoseStamped navigation goal."""
        position = command.get("position", {})
        x = float(position.get("x", 0.0))
        y = float(position.get("y", 0.0))
        theta = float(position.get("theta", 0.0))

        # Convert theta (yaw) to quaternion for PoseStamped
        qz = math.sin(theta / 2.0)
        qw = math.cos(theta / 2.0)

        topic = roslibpy.Topic(
            self._ros,
            self.topic_navigate,
            "geometry_msgs/PoseStamped",
        )
        topic.publish(
            roslibpy.Message(
                {
                    "header": {
                        "frame_id": command.get("frame_id", "map"),
                    },
                    "pose": {
                        "position": {"x": x, "y": y, "z": 0.0},
                        "orientation": {
                            "x": 0.0,
                            "y": 0.0,
                            "z": qz,
                            "w": qw,
                        },
                    },
                }
            )
        )
        topic.unadvertise()
        self.logger.info(f"Navigation goal published: x={x}, y={y}, θ={theta}")
        return True

    def _publish_stop(self) -> bool:
        """Publish zero-velocity Twist to stop the base."""
        topic = roslibpy.Topic(self._ros, self.topic_cmd_vel, "geometry_msgs/Twist")
        topic.publish(
            roslibpy.Message(
                {
                    "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
                }
            )
        )
        topic.unadvertise()
        self.logger.info("Stop command published (zero velocity)")
        return True

    def _publish_pick_sequence(self, command: Dict[str, Any]) -> bool:
        """Publish a pick sequence: extend arm, then close gripper.

        The pick height/extension can be specified in the command payload.
        """
        lift_height = float(command.get("lift_height", 0.6))
        arm_extension = float(command.get("arm_extension", 0.3))

        # Step 1: Move arm to pick position
        self._publish_joint_trajectory(
            {
                "joint_names": ["joint_lift", "joint_arm_l0"],
                "positions": [lift_height, arm_extension],
                "duration": float(command.get("duration", 4.0)),
            }
        )

        # Step 2: Close gripper
        self._publish_gripper_command({"state": "close", "effort": 50.0})

        self.logger.info(f"Pick sequence published: lift={lift_height}, ext={arm_extension}")
        return True

    def _publish_place_sequence(self, command: Dict[str, Any]) -> bool:
        """Publish a place sequence: extend arm, then open gripper."""
        lift_height = float(command.get("lift_height", 0.6))
        arm_extension = float(command.get("arm_extension", 0.3))

        # Step 1: Move arm to place position
        self._publish_joint_trajectory(
            {
                "joint_names": ["joint_lift", "joint_arm_l0"],
                "positions": [lift_height, arm_extension],
                "duration": float(command.get("duration", 4.0)),
            }
        )

        # Step 2: Open gripper
        self._publish_gripper_command({"state": "open", "effort": 50.0})

        self.logger.info(f"Place sequence published: lift={lift_height}, ext={arm_extension}")
        return True

    def _publish_home_position(self) -> bool:
        """Send all joints to the Stretch stow/home configuration."""
        home_joints = {
            "joint_names": [
                "joint_lift",
                "joint_arm_l0",
                "joint_wrist_yaw",
                "joint_head_pan",
                "joint_head_tilt",
            ],
            "positions": [
                0.3,  # lift — low stow position
                0.0,  # arm — fully retracted
                3.14,  # wrist — rotated to stow
                0.0,  # head pan — centered
                -0.5,  # head tilt — slightly down
            ],
            "duration": 6.0,
        }
        self._publish_joint_trajectory(home_joints)
        self._publish_gripper_command({"state": "close", "effort": 30.0})
        self.logger.info("Home/stow position published")
        return True

    def _publish_joint_trajectory(self, command: Dict[str, Any]) -> bool:
        """Publish a JointTrajectory message for arm/head control."""
        joint_names: List[str] = command.get("joint_names", [])
        positions: List[float] = command.get("positions", [])
        duration: float = float(command.get("duration", 4.0))

        if not joint_names or len(joint_names) != len(positions):
            self.logger.error("joint_names and positions must be non-empty and equal length")
            return False

        # Convert duration to secs + nsecs
        secs = int(duration)
        nsecs = int((duration - secs) * 1e9)

        topic = roslibpy.Topic(
            self._ros,
            self.topic_joint_trajectory,
            "trajectory_msgs/JointTrajectory",
        )
        topic.publish(
            roslibpy.Message(
                {
                    "joint_names": joint_names,
                    "points": [
                        {
                            "positions": positions,
                            "velocities": [0.0] * len(positions),
                            "time_from_start": {
                                "secs": secs,
                                "nsecs": nsecs,
                            },
                        }
                    ],
                }
            )
        )
        topic.unadvertise()
        self.logger.debug(f"JointTrajectory published: joints={joint_names}, pos={positions}")
        return True

    def _publish_gripper_command(self, command: Dict[str, Any]) -> bool:
        """Publish a GripperCommand to open or close the gripper."""
        state = command.get("state", "close")
        effort = float(command.get("effort", 50.0))

        # Stretch gripper: positive position = open, ~0 = closed
        gripper_position = 0.165 if state == "open" else 0.0

        topic = roslibpy.Topic(
            self._ros,
            self.topic_gripper,
            "control_msgs/GripperCommand",
        )
        topic.publish(
            roslibpy.Message(
                {
                    "command": {
                        "position": gripper_position,
                        "max_effort": effort,
                    }
                }
            )
        )
        topic.unadvertise()
        self.logger.debug(f"Gripper command published: state={state}")
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _quaternion_to_yaw(q: Dict[str, float]) -> float:
        """Convert a quaternion dict {x, y, z, w} to yaw (heading) in radians."""
        qx = q.get("x", 0.0)
        qy = q.get("y", 0.0)
        qz = q.get("z", 0.0)
        qw = q.get("w", 1.0)

        # Standard quaternion-to-yaw conversion
        siny_cosp = 2.0 * (qw * qz + qx * qy)
        cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
        return math.atan2(siny_cosp, cosy_cosp)

    def _map_vendor_status(self, vendor_status: str) -> str:
        """Map ROS-level status strings to Mosoro standard status.

        Returns one of: idle, moving, working, charging, error, offline
        """
        status_map = {
            "idle": self._STATUS_IDLE,
            "navigating": self._STATUS_MOVING,
            "moving": self._STATUS_MOVING,
            "manipulating": self._STATUS_WORKING,
            "working": self._STATUS_WORKING,
            "charging": self._STATUS_CHARGING,
            "error": self._STATUS_ERROR,
            "fault": self._STATUS_ERROR,
            "offline": self._STATUS_OFFLINE,
            "disconnected": self._STATUS_OFFLINE,
        }
        return status_map.get(vendor_status.lower(), self._STATUS_IDLE)
