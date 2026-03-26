# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0

"""
Adapter Contract Tests
=======================

Validates that all community adapters conform to the BaseMosoroAdapter
interface and produce data compatible with the MosoroPayload schema.
"""

import pytest
from mosoro_core.base_adapter import BaseMosoroAdapter
from mosoro_core.models import MosoroPayload, Position

from adapters.fetch import FetchAdapter
from adapters.geekplus import GeekplusAdapter
from adapters.locus import LocusAdapter
from adapters.mir import MirAdapter
from adapters.stretch import StretchAdapter


# ---------------------------------------------------------------------------
# Shared contract tests
# ---------------------------------------------------------------------------

class AdapterContractTests:
    """Base test class for adapter contract validation.

    Subclass this and implement the `adapter_class` attribute to test your adapter.
    """

    adapter_class: type = None

    def test_is_subclass_of_base(self):
        """Adapter must subclass BaseMosoroAdapter."""
        assert self.adapter_class is not None, "adapter_class must be set"
        assert issubclass(self.adapter_class, BaseMosoroAdapter)

    def test_has_vendor_name(self):
        """Adapter must declare a vendor_name."""
        assert hasattr(self.adapter_class, "vendor_name")
        assert self.adapter_class.vendor_name != "unknown"

    def test_instantiation(self):
        """Adapter must be instantiable with robot_id and config."""
        config = {
            "vendor": self.adapter_class.vendor_name,
            "api_base_url": "http://localhost:8080",
        }
        adapter = self.adapter_class("test-001", config)
        assert adapter.robot_id == "test-001"
        assert adapter.vendor == self.adapter_class.vendor_name

    def test_has_required_methods(self):
        """Adapter must implement all required abstract methods."""
        config = {
            "vendor": self.adapter_class.vendor_name,
            "api_base_url": "http://localhost:8080",
        }
        adapter = self.adapter_class("test-001", config)

        assert hasattr(adapter, "_fetch_robot_status")
        assert callable(adapter._fetch_robot_status)
        assert hasattr(adapter, "send_command")
        assert callable(adapter.send_command)
        assert hasattr(adapter, "get_normalized_status")
        assert callable(adapter.get_normalized_status)
        assert hasattr(adapter, "handle_command")
        assert callable(adapter.handle_command)

    def test_has_lifecycle_methods(self):
        """Adapter should have connect/disconnect lifecycle methods."""
        config = {
            "vendor": self.adapter_class.vendor_name,
            "api_base_url": "http://localhost:8080",
        }
        adapter = self.adapter_class("test-001", config)

        assert hasattr(adapter, "connect")
        assert callable(adapter.connect)
        assert hasattr(adapter, "disconnect")
        assert callable(adapter.disconnect)


# ---------------------------------------------------------------------------
# Per-adapter test classes
# ---------------------------------------------------------------------------

class TestFetchAdapterContract(AdapterContractTests):
    adapter_class = FetchAdapter

    def test_vendor_name(self):
        assert FetchAdapter.vendor_name == "fetch"


class TestGeekplusAdapterContract(AdapterContractTests):
    adapter_class = GeekplusAdapter

    def test_vendor_name(self):
        assert GeekplusAdapter.vendor_name == "geekplus"


class TestLocusAdapterContract(AdapterContractTests):
    adapter_class = LocusAdapter

    def test_vendor_name(self):
        assert LocusAdapter.vendor_name == "locus"


class TestMirAdapterContract(AdapterContractTests):
    adapter_class = MirAdapter

    def test_vendor_name(self):
        assert MirAdapter.vendor_name == "mir"


class TestStretchAdapterContract(AdapterContractTests):
    adapter_class = StretchAdapter

    def test_vendor_name(self):
        assert StretchAdapter.vendor_name == "stretch"


# ---------------------------------------------------------------------------
# Status data validation tests (using Stretch since it has placeholder data)
# ---------------------------------------------------------------------------

class TestStretchStatusData:
    """Test that Stretch adapter's placeholder data validates against MosoroPayload."""

    @pytest.fixture
    def adapter(self):
        config = {"vendor": "stretch", "ros_bridge_url": "http://localhost:9090"}
        return StretchAdapter("stretch-test", config)

    @pytest.mark.asyncio
    async def test_status_returns_dict(self, adapter):
        status = await adapter._fetch_robot_status()
        assert isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_status_has_valid_position(self, adapter):
        status = await adapter._fetch_robot_status()
        assert "position" in status
        pos = status["position"]
        assert isinstance(pos["x"], (int, float))
        assert isinstance(pos["y"], (int, float))

    @pytest.mark.asyncio
    async def test_status_has_valid_battery(self, adapter):
        status = await adapter._fetch_robot_status()
        assert "battery" in status
        assert 0.0 <= status["battery"] <= 100.0

    @pytest.mark.asyncio
    async def test_status_has_valid_status_enum(self, adapter):
        status = await adapter._fetch_robot_status()
        valid_statuses = {"idle", "moving", "working", "charging", "error", "offline"}
        assert status["status"] in valid_statuses

    @pytest.mark.asyncio
    async def test_payload_validates_as_mosoro(self, adapter):
        status = await adapter._fetch_robot_status()
        payload = MosoroPayload(**status)
        assert payload is not None
