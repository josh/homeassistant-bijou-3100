import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BijouClient, BijouError, BijouState
from .const import DEFAULT_MODEL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The amplifier acknowledges a command before applying it. Volume lands within
# milliseconds, but DSP changes such as the audio mode take a few hundred, and
# delay anything queued behind them, so confirmation is polled rather than read
# once.
CONFIRM_DELAYS = (0.0, 0.15, 0.35, 0.75, 1.5)


class BijouCoordinator(DataUpdateCoordinator[BijouState]):
    def __init__(
        self, hass: HomeAssistant, entry: BijouConfigEntry, client: BijouClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
            always_update=False,
        )
        self._operation_lock = asyncio.Lock()
        self.client = client
        self.model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        self.expected_serial = entry.unique_id

    async def _async_fetch(self) -> BijouState:
        try:
            state = await self.client.fetch()
        except BijouError as err:
            raise UpdateFailed(str(err)) from err
        if state.serial != self.expected_serial:
            raise UpdateFailed("The address now belongs to a different amplifier")
        return state

    async def _async_update_data(self) -> BijouState:
        async with self._operation_lock:
            return await self._async_fetch()

    async def _async_confirm(self, expect: Callable[[BijouState], bool]) -> BijouState:
        for delay in CONFIRM_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            state = await self._async_fetch()
            if expect(state):
                break
        return state

    async def async_send(
        self, command: str, expect: Callable[[BijouState], bool]
    ) -> None:
        async with self._operation_lock:
            try:
                await self.client.send(command)
                state = await self._async_confirm(expect)
            except (BijouError, UpdateFailed) as err:
                self.async_set_update_error(UpdateFailed(str(err)))
                raise HomeAssistantError(
                    f"Command {command!r} could not be verified: {err}. "
                    "Check the amplifier before retrying"
                ) from err
            self.async_set_updated_data(state)
            if not expect(state):
                raise HomeAssistantError(
                    f"The amplifier acknowledged {command!r} but did not apply it"
                )


type BijouConfigEntry = ConfigEntry[BijouCoordinator]
