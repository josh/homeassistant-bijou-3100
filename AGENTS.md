# Development

Media player, sensors, and audio controls for the AudioControl Bijou 3100. Keep documentation minimal and never hard-wrap Markdown.

Targets the latest Home Assistant release only. `requires-python` mirrors Home Assistant's own value, so raising one means raising the other.

```sh
uv sync --locked
uv run ruff format --diff .
uv run ruff check .
uv run mypy .
```

There are no tests. `mypy --strict` against the locked Home Assistant is the gate that catches API drift.

Run these locally before committing; neither is installed by `uv sync` or checked in CI.

```sh
uvx ssort .
uvx pyproject-fmt pyproject.toml
```

Sort functions in dependency order. Avoid superfluous comments and docstrings; only include them when they clarify complex logic.

## Device API

The amplifier serves an lwIP HTTP server on port 80. State is read as JSON from `/ssi/mainpage.ssi`, `/ssi/infopage.ssi`, and `/ssi/eqpage.ssi`; every value is a string. Commands are sent as `GET /cmd?SET%20VOL%2050`, which always returns `OK` even for invalid commands and out-of-range values, so every write is verified by re-reading state.

The amplifier acknowledges a command before applying it. Volume lands within milliseconds, but DSP changes such as the audio mode take a few hundred and delay anything queued behind them, so `BijouCoordinator` polls for confirmation across `CONFIRM_DELAYS` rather than reading back once. Measured worst case is about 700 ms.

With `HVOL FOLLOW` on, `SET MUTE` also mutes the headphone output but `SET UNMUTE` does not unmute it.

A documented telnet command set on port 23 covers the same ground and remains a fallback.
