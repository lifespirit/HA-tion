"""One shared Bluetooth transaction gate for every Tion entry and config flow."""

import asyncio
from contextlib import asynccontextmanager

from .const import DOMAIN


class TionBluetoothGate:
    """Serialize Tion sessions and recover a client before admitting another."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._pending = None

    @asynccontextmanager
    async def transaction(self, tion=None):
        async with self._lock:
            if self._pending is not None:
                await self._pending.close()
                self._pending = None
            try:
                yield
            finally:
                if tion is not None and tion.has_pending_connection:
                    self._pending = tion


def bluetooth_gate(hass) -> TionBluetoothGate:
    return hass.data.setdefault(DOMAIN, {}).setdefault("bluetooth_gate", TionBluetoothGate())
