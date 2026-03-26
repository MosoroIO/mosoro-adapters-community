# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0

"""
Shared Adapter Contract Tests
===============================

These tests validate that any adapter implementation conforms to the
MosoroMessage schema contract. Import and run these against your adapter.
"""

import pytest
from mosoro_core.models import MosoroPayload, Position


class AdapterContractTests:
    """Base test class for adapter contract validation.
    
    Subclass this and implement the `adapter` fixture to test your adapter.
    """

    def test_poll_status_returns_dict(self, adapter_status):
        """poll_status() must return a dict."""
        assert isinstance(adapter_status, dict)

    def test_status_has_valid_position(self, adapter_status):
        """If position is present, it must have x and y."""
        if "position" in adapter_status and adapter_status["position"]:
            pos = adapter_status["position"]
            assert "x" in pos
            assert "y" in pos
            assert isinstance(pos["x"], (int, float))
            assert isinstance(pos["y"], (int, float))

    def test_status_has_valid_battery(self, adapter_status):
        """If battery is present, it must be 0-100."""
        if "battery" in adapter_status and adapter_status["battery"] is not None:
            assert 0.0 <= adapter_status["battery"] <= 100.0

    def test_status_has_valid_status_enum(self, adapter_status):
        """If status is present, it must be a valid MosoroMessage status."""
        valid_statuses = {"idle", "moving", "working", "charging", "error", "offline"}
        if "status" in adapter_status and adapter_status["status"]:
            assert adapter_status["status"] in valid_statuses

    def test_payload_validates_as_mosoro(self, adapter_status):
        """The status dict must be valid as a MosoroPayload."""
        # This will raise ValidationError if the data doesn't conform
        payload = MosoroPayload(**adapter_status)
        assert payload is not None
