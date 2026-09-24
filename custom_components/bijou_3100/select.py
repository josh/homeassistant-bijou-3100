from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BijouState
from .const import (
    DOMAIN,
    LINE_OUTPUT_GAIN_ARGS,
    POWER_OFF_TIMER_ARGS,
    POWER_RECOVERY_ARGS,
)
from .coordinator import BijouConfigEntry, BijouCoordinator

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class BijouSelectEntityDescription(SelectEntityDescription):
    value_fn: Callable[[BijouState], str | None]
    command_fn: Callable[[str], str]


DESCRIPTIONS = (
    BijouSelectEntityDescription(
        key="line_output_gain",
        translation_key="line_output_gain",
        entity_category=EntityCategory.CONFIG,
        options=list(LINE_OUTPUT_GAIN_ARGS),
        value_fn=lambda state: state.line_output_gain,
        command_fn=lambda option: f"SET LINEOUT LEVEL {LINE_OUTPUT_GAIN_ARGS[option]}",
    ),
    BijouSelectEntityDescription(
        key="power_recovery",
        translation_key="power_recovery",
        entity_category=EntityCategory.CONFIG,
        options=list(POWER_RECOVERY_ARGS),
        value_fn=lambda state: state.power_recovery,
        command_fn=lambda option: f"SET POWER RECOVERY {POWER_RECOVERY_ARGS[option]}",
    ),
    BijouSelectEntityDescription(
        key="power_off_timer",
        translation_key="power_off_timer",
        entity_category=EntityCategory.CONFIG,
        options=list(POWER_OFF_TIMER_ARGS),
        value_fn=lambda state: state.power_off_timer,
        command_fn=lambda option: f"SET POWER OFF TIMER {POWER_OFF_TIMER_ARGS[option]}",
    ),
)


class BijouSelect(CoordinatorEntity[BijouCoordinator], SelectEntity):
    _attr_has_entity_name = True
    entity_description: BijouSelectEntityDescription

    def __init__(
        self, coordinator: BijouCoordinator, description: BijouSelectEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        serial = coordinator.data.serial
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)})

    @property
    def current_option(self) -> str | None:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        description = self.entity_description
        await self.coordinator.async_send(
            description.command_fn(option),
            lambda state: description.value_fn(state) == option,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BijouConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(BijouSelect(entry.runtime_data, item) for item in DESCRIPTIONS)
