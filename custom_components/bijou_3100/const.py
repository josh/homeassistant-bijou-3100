from typing import Final, TypedDict

DOMAIN = "bijou_3100"
MANUFACTURER = "AudioControl"
DEFAULT_MODEL = "Bijou 3100"
DEFAULT_SCAN_INTERVAL = 10


class MainPage(TypedDict):
    powerstate: str
    spvolume: str
    spmute: str
    submute: str
    hpvolume: str
    hpmute: str
    hpvolfollow: str
    audiosel: str
    audiomode: str
    audioinformat: str
    audioout: str
    serial: str
    hostname: str
    macaddr: str
    mcuversion: str
    dspversion: str


class InfoPage(TypedDict):
    tsense: str


class EqPage(TypedDict):
    eqenable: str


SOURCES: Final[dict[str, str]] = {
    "0": "eARC",
    "1": "Digital",
    "2": "Analog",
    "3": "Dante",
}
SOURCE_ARGS: Final[dict[str, str]] = {
    "eARC": "EARC",
    "Digital": "DIGITAL",
    "Analog": "ANALOG",
    "Dante": "DANTE",
}
DEFAULT_SOURCES: Final[tuple[str, ...]] = ("eARC", "Digital", "Analog")

# The 5100D is the only model in the series with a Dante input. Other models share
# this API, but nothing here has been tested against them.
MODEL_SOURCES: Final[dict[str, tuple[str, ...]]] = {
    "Bijou 5100D": ("eARC", "Digital", "Analog", "Dante"),
}

SOUND_MODES: Final[dict[str, str]] = {
    "0": "Native",
    "1": "2-Channel Stereo",
    "2": "All-Channel Stereo",
    "3": "Dolby Surround",
    "4": "Dolby Mode",
}
SOUND_MODE_ARGS: Final[dict[str, str]] = {
    "Native": "NATIVE",
    "2-Channel Stereo": "2CHSTEREO",
    "All-Channel Stereo": "ALLCHSTEREO",
    "Dolby Surround": "DOLBY SURROUND",
    "Dolby Mode": "DOLBY MODE",
}
