from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BijouState
from .const import DOMAIN
from .coordinator import BijouConfigEntry, BijouCoordinator

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class BijouNumberEntityDescription(NumberEntityDescription):
    value_fn: Callable[[BijouState], int]
    command_fn: Callable[[int], str]


DESCRIPTIONS = (
    BijouNumberEntityDescription(
        key="on_volume",
        translation_key="on_volume",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda state: state.on_volume,
        command_fn=lambda value: f"SET ON VOL {value}",
    ),
    BijouNumberEntityDescription(
        key="max_volume",
        translation_key="max_volume",
        entity_category=EntityCategory.CONFIG,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda state: state.max_volume,
        command_fn=lambda value: f"SET MAX VOL {value}",
    ),
)


class BijouNumber(CoordinatorEntity[BijouCoordinator], NumberEntity):
    _attr_has_entity_name = True
    entity_description: BijouNumberEntityDescription

    def __init__(
        self, coordinator: BijouCoordinator, description: BijouNumberEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        serial = coordinator.data.serial
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)})

    @property
    def native_value(self) -> int:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        description = self.entity_description
        target = int(value)
        await self.coordinator.async_send(
            description.command_fn(target),
            lambda state: description.value_fn(state) == target,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BijouConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(BijouNumber(entry.runtime_data, item) for item in DESCRIPTIONS)
