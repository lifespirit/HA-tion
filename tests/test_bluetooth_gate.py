"""Gate lifecycle tests without importing the whole Home Assistant runtime."""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest


def load_gate():
    package = types.ModuleType("tion_gate_test")
    package.__path__ = []
    const = types.ModuleType("tion_gate_test.const")
    const.DOMAIN = "ha_tion_btle"
    sys.modules[package.__name__] = package
    sys.modules[const.__name__] = const
    path = Path(__file__).parents[1] / "custom_components/ha_tion_btle/bluetooth_gate.py"
    spec = importlib.util.spec_from_file_location("tion_gate_test.bluetooth_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_four_devices_use_one_gate():
    gate = load_gate().TionBluetoothGate()
    active = 0
    maximum = 0

    async def operation():
        nonlocal active, maximum
        async with gate.transaction():
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0)
            active -= 1

    await asyncio.gather(*(operation() for _ in range(100)))
    assert maximum == 1


@pytest.mark.asyncio
async def test_failed_teardown_is_recovered_before_next_connection():
    gate = load_gate().TionBluetoothGate()

    class ClientOwner:
        has_pending_connection = True
        closed = False

        async def close(self):
            self.closed = True
            self.has_pending_connection = False

    old = ClientOwner()
    async with gate.transaction(old):
        pass

    async with gate.transaction():
        assert old.closed


@pytest.mark.asyncio
async def test_failed_recovery_blocks_next_connection():
    gate = load_gate().TionBluetoothGate()

    class ClientOwner:
        has_pending_connection = True

        async def close(self):
            raise RuntimeError("disconnect failed")

    async with gate.transaction(ClientOwner()):
        pass
    with pytest.raises(RuntimeError, match="disconnect failed"):
        async with gate.transaction():
            pytest.fail("new connection must not start")
