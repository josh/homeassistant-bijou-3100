from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_SOURCES,
    DOMAIN,
    MANUFACTURER,
    MODEL_SOURCES,
    SOUND_MODE_ARGS,
    SOURCE_ARGS,
)
from .coordinator import BijouConfigEntry, BijouCoordinator

PARALLEL_UPDATES = 1


class BijouMediaPlayer(CoordinatorEntity[BijouCoordinator], MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, coordinator: BijouCoordinator) -> None:
        super().__init__(coordinator)
        state = coordinator.data
        self._attr_unique_id = state.serial
        self._attr_source_list = list(
            MODEL_SOURCES.get(coordinator.model, DEFAULT_SOURCES)
        )
        self._attr_sound_mode_list = list(SOUND_MODE_ARGS)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, state.serial)},
            name=coordinator.model,
            manufacturer=MANUFACTURER,
            model=coordinator.model,
            serial_number=state.serial,
            sw_version=f"MCU {state.mcu_version} / DSP {state.dsp_version}",
            configuration_url=f"http://{coordinator.client.host}",
        )

    @property
    def state(self) -> MediaPlayerState:
        return (
            MediaPlayerState.ON if self.coordinator.data.is_on else MediaPlayerState.OFF
        )

    @property
    def volume_level(self) -> float:
        return self.coordinator.data.volume / 100

    @property
    def is_volume_muted(self) -> bool:
        return self.coordinator.data.is_muted

    @property
    def source(self) -> str | None:
        return self.coordinator.data.source

    @property
    def sound_mode(self) -> str | None:
        return self.coordinator.data.sound_mode

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        state = self.coordinator.data
        formats = {
            "input_format": state.input_format,
            "output_format": state.output_format,
        }
        return {k: v for k, v in formats.items() if v is not None}

    async def async_turn_on(self) -> None:
        await self.coordinator.async_send("SET POWER ON", lambda state: state.is_on)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_send(
            "SET POWER OFF", lambda state: not state.is_on
        )

    async def async_set_volume_level(self, volume: float) -> None:
        level = round(volume * 100)
        await self.coordinator.async_send(
            f"SET VOL {level}", lambda state: state.volume == level
        )

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.async_send(
            "SET MUTE" if mute else "SET UNMUTE",
            lambda state: state.is_muted is mute,
        )

    async def async_select_source(self, source: str) -> None:
        await self.coordinator.async_send(
            f"SET INPUT {SOURCE_ARGS[source]}", lambda state: state.source == source
        )

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        await self.coordinator.async_send(
            f"SET AUDIO MODE {SOUND_MODE_ARGS[sound_mode]}",
            lambda state: state.sound_mode == sound_mode,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BijouConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([BijouMediaPlayer(entry.runtime_data)])
