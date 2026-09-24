from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BijouState
from .const import DOMAIN
from .coordinator import BijouConfigEntry, BijouCoordinator

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BijouSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[BijouState], str | int | None]


DESCRIPTIONS = (
    BijouSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.temperature,
    ),
    BijouSensorEntityDescription(
        key="input_format",
        translation_key="input_format",
        value_fn=lambda state: state.input_format or None,
    ),
    BijouSensorEntityDescription(
        key="output_format",
        translation_key="output_format",
        value_fn=lambda state: state.output_format or None,
    ),
)


class BijouSensor(CoordinatorEntity[BijouCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: BijouSensorEntityDescription

    def __init__(
        self, coordinator: BijouCoordinator, description: BijouSensorEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        serial = coordinator.data.serial
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)})

    @property
    def native_value(self) -> str | int | None:
        return self.entity_description.value_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BijouConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(BijouSensor(entry.runtime_data, item) for item in DESCRIPTIONS)
