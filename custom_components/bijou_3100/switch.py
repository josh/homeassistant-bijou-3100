from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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
class BijouSwitchEntityDescription(SwitchEntityDescription):
    value_fn: Callable[[BijouState], bool]
    command_fn: Callable[[bool], str]


DESCRIPTIONS = (
    BijouSwitchEntityDescription(
        key="subwoofer_mute",
        translation_key="subwoofer_mute",
        value_fn=lambda state: state.subwoofer_muted,
        command_fn=lambda on: "SET SUB MUTE" if on else "SET SUB UNMUTE",
    ),
    BijouSwitchEntityDescription(
        key="headphone_mute",
        translation_key="headphone_mute",
        value_fn=lambda state: state.headphone_muted,
        command_fn=lambda on: "SET HMUTE" if on else "SET HUNMUTE",
    ),
    BijouSwitchEntityDescription(
        key="headphone_volume_follow",
        translation_key="headphone_volume_follow",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.headphone_follow,
        command_fn=lambda on: f"SET HVOL FOLLOW {'ON' if on else 'OFF'}",
    ),
    BijouSwitchEntityDescription(
        key="equalizer",
        translation_key="equalizer",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.eq_enabled,
        command_fn=lambda on: f"SET EQ {'ENABLE' if on else 'DISABLE'}",
    ),
)


class BijouSwitch(CoordinatorEntity[BijouCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    entity_description: BijouSwitchEntityDescription

    def __init__(
        self, coordinator: BijouCoordinator, description: BijouSwitchEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        serial = coordinator.data.serial
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)})

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data)

    async def _async_set(self, on: bool) -> None:
        description = self.entity_description
        await self.coordinator.async_send(
            description.command_fn(on), lambda state: description.value_fn(state) is on
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BijouConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(BijouSwitch(entry.runtime_data, item) for item in DESCRIPTIONS)
