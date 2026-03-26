# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0

"""
Template Robot Adapter
=======================

Copy this directory as a starting point for your adapter.
Rename to {vendor}/ and implement all abstract methods.

Steps:
    1. Copy this directory: cp -r adapters/_template adapters/my_vendor
    2. Rename this file: mv template_adapter.py my_vendor_adapter.py
    3. Rename the class to MyVendorAdapter
    4. Implement _fetch_robot_status() and send_command()
    5. Update __init__.py to export your class
    6. Register in pyproject.toml entry points
    7. Add tests in tests/
"""

from typing import Any, Dict

from mosoro_core.base_adapter import BaseMosoroAdapter


class TemplateAdapter(BaseMosoroAdapter):
    """
    Template adapter — replace with your vendor name.

    Subclasses BaseMosoroAdapter from mosoro-core.
    You must implement _fetch_robot_status() and send_command().
    """

    vendor_name = "template"

    def __init__(self, robot_id: str, config: Dict[str, Any]) -> None:
        super().__init__(robot_id, config)
        self.base_url = config.get("api_base_url", "http://localhost:8080")

    async def connect(self) -> bool:
        """Establish connection to the robot's API."""
        # TODO: Implement connection logic (e.g., create aiohttp session)
        self.connected = True
        self.logger.info(f"Template adapter {self.robot_id} connected to {self.base_url}")
        return True

    async def disconnect(self) -> None:
        """Disconnect from the robot's API."""
        # TODO: Implement disconnection logic (e.g., close aiohttp session)
        self.connected = False
        self.logger.info(f"Template adapter {self.robot_id} disconnected")

    async def _fetch_robot_status(self) -> Dict[str, Any]:
        """Poll the robot for current status.

        Returns a dict that maps to MosoroPayload fields:
        - position: {x, y, z, theta, map_id}
        - battery: float (0-100)
        - status: idle | moving | working | charging | error | offline
        - current_task: {task_id, task_type, progress}
        - health: str
        - errors: [{code, message}]
        - vendor_specific: dict
        """
        # TODO: Call vendor API and translate response
        return {
            "position": {"x": 0.0, "y": 0.0},
            "battery": 100.0,
            "status": "idle",
        }

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send a command to the robot.

        Args:
            command: MosoroMessage command payload

        Returns:
            True if command was accepted, False otherwise
        """
        action = command.get("action")
        self.logger.info(f"Sending {action} command to template robot {self.robot_id}")

        # TODO: Translate MosoroMessage command to vendor format and send
        if action == "move_to":
            # Example: send navigation command
            return True
        elif action == "pause":
            return True
        elif action == "resume":
            return True

        self.logger.warning(f"Unsupported command: {action}")
        return False

    def _map_vendor_status(self, vendor_status: str) -> str:
        """Map vendor-specific status to Mosoro status enum.

        Must return one of: idle, moving, working, charging, error, offline
        """
        status_map = {
            # "vendor_status": "mosoro_status",
            "ready": "idle",
            "navigating": "moving",
            "executing": "working",
            "charging": "charging",
            "fault": "error",
            "disconnected": "offline",
        }
        return status_map.get(vendor_status, "idle")
