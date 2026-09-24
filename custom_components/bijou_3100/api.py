import asyncio
import re
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import SOUND_MODES, SOURCES, EqPage, InfoPage, MainPage

TIMEOUT = ClientTimeout(total=10)
TITLE_PATTERN = re.compile(r"<title>([^<]+)</title>", re.IGNORECASE)


class BijouError(Exception):
    pass


class CannotConnect(BijouError):
    pass


class InvalidResponse(BijouError):
    pass


class UnsupportedModel(BijouError):
    pass


def validate_host(host: str) -> str:
    host = host.strip().lower()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", host):
        raise ValueError("Enter an IPv4 address or hostname without a scheme or port")
    return host


@dataclass(frozen=True)
class BijouState:
    serial: str
    hostname: str
    mac_address: str
    mcu_version: str
    dsp_version: str
    is_on: bool
    volume: int
    is_muted: bool
    headphone_volume: int
    headphone_muted: bool
    headphone_follow: bool
    subwoofer_muted: bool
    source: str | None
    sound_mode: str | None
    input_format: str | None
    output_format: str | None
    temperature: int | None
    eq_enabled: bool


def _as_int(value: str) -> int:
    try:
        return int(float(value))
    except ValueError as err:
        raise InvalidResponse(f"Expected a number, got {value!r}") from err


def _as_optional_int(value: str) -> int | None:
    try:
        return int(float(value))
    except ValueError:
        return None


def parse_state(main: MainPage, info: InfoPage, eq: EqPage) -> BijouState:
    return BijouState(
        serial=main["serial"],
        hostname=main["hostname"],
        mac_address=main["macaddr"].lower(),
        mcu_version=main["mcuversion"],
        dsp_version=main["dspversion"],
        is_on=main["powerstate"] == "1",
        volume=_as_int(main["spvolume"]),
        is_muted=main["spmute"] == "1",
        headphone_volume=_as_int(main["hpvolume"]),
        headphone_muted=main["hpmute"] == "1",
        headphone_follow=main["hpvolfollow"] == "1",
        subwoofer_muted=main["submute"] == "1",
        source=SOURCES.get(main["audiosel"]),
        sound_mode=SOUND_MODES.get(main["audiomode"]),
        input_format=main["audioinformat"] or None,
        output_format=main["audioout"] or None,
        temperature=_as_optional_int(info["tsense"]),
        eq_enabled=eq["eqenable"] == "1",
    )


class BijouClient:
    def __init__(self, session: ClientSession, host: str) -> None:
        self._session = session
        self.host = host

    async def _fetch_page(self, page: str, required: frozenset[str]) -> dict[str, Any]:
        url = f"http://{self.host}/ssi/{page}.ssi"
        try:
            async with self._session.get(url, timeout=TIMEOUT) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError) as err:
            raise CannotConnect(f"Could not reach {url}: {err}") from err
        except ValueError as err:
            raise InvalidResponse(f"{url} did not return JSON") from err
        if not isinstance(payload, dict):
            raise InvalidResponse(f"{url} did not return a JSON object")
        missing = required - payload.keys()
        if missing:
            raise UnsupportedModel(f"{url} is missing {', '.join(sorted(missing))}")
        return cast(dict[str, Any], payload)

    async def fetch(self) -> BijouState:
        main, info, eq = await asyncio.gather(
            self._fetch_page("mainpage", MainPage.__required_keys__),
            self._fetch_page("infopage", InfoPage.__required_keys__),
            self._fetch_page("eqpage", EqPage.__required_keys__),
        )
        state = parse_state(
            cast(MainPage, main), cast(InfoPage, info), cast(EqPage, eq)
        )
        if not state.serial:
            raise UnsupportedModel("The device did not report a serial number")
        return state

    async def _get(self, url: str) -> str:
        try:
            async with self._session.get(url, timeout=TIMEOUT) as response:
                response.raise_for_status()
                return await response.text()
        except (ClientError, TimeoutError) as err:
            raise CannotConnect(f"Could not reach {url}: {err}") from err

    async def fetch_model(self) -> str:
        body = await self._get(f"http://{self.host}/")
        match = TITLE_PATTERN.search(body)
        if match is None:
            raise UnsupportedModel("The device did not report a model name")
        return match.group(1).strip()

    async def send(self, command: str) -> None:
        # /cmd always answers "OK", even for unknown commands and out-of-range
        # values, so callers must confirm the result by re-reading state.
        body = await self._get(f"http://{self.host}/cmd?{quote(command)}")
        if body.strip() != "OK":
            raise InvalidResponse(f"Command {command!r} returned {body.strip()!r}")
