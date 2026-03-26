# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0

"""
Template Robot Adapter
=======================

Copy this file as a starting point for your adapter.
Rename to {vendor}_adapter.py and implement all methods.
"""

from typing import Any, Dict, Optional

# When mosoro-core is installed:
# from agents.adapters.base_adapter import BaseMosoroAdapter
# from mosoro_core.models import MosoroPayload, Position


class TemplateAdapter:
    """
    Template adapter — replace with your vendor name.
    
    In production, this should subclass BaseMosoroAdapter from mosoro-core.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.base_url = config.get("base_url", "http://localhost:8080")
        self.robot_id = config.get("robot_id", "template-001")

    async def connect(self) -> None:
        """Establish connection to the robot's API."""
        # TODO: Implement connection logic
        pass

    async def disconnect(self) -> None:
        """Disconnect from the robot's API."""
        # TODO: Implement disconnection logic
        pass

    async def poll_status(self) -> Dict[str, Any]:
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
        # TODO: Translate MosoroMessage command to vendor format and send
        return True

    def map_vendor_status(self, vendor_status: str) -> str:
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
