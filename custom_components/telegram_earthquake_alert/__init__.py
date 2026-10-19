"""Telegram Earthquake Alert integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from telethon import TelegramClient, events
from telethon.errors import RPCError, UnauthorizedError
from telethon.sessions import StringSession

from .const import (
    ALERT_DEBOUNCE_SECONDS,
    CONF_API_HASH,
    CONF_API_ID,
    CONF_DIALOGS,
    CONF_SESSION_STRING,
    DOMAIN,
)
from .parser import find_magnitude

_LOGGER = logging.getLogger(__name__)

type MessageHandler = Callable[[Any], Awaitable[None]]


@dataclass(slots=True)
class TelegramEarthquakeAlertRuntimeData:
    """Runtime data for a config entry."""

    client: TelegramClient
    message_handler: MessageHandler


type TelegramEarthquakeAlertConfigEntry = ConfigEntry[
    TelegramEarthquakeAlertRuntimeData
]


async def _async_disconnect(client: TelegramClient) -> None:
    """Disconnect a Telegram client without masking the original error."""
    try:
        await client.disconnect()
    except Exception:  # Telethon may fail while tearing down a broken connection.
        _LOGGER.debug("Error disconnecting from Telegram", exc_info=True)


async def async_setup_entry(
    hass: HomeAssistant, entry: TelegramEarthquakeAlertConfigEntry
) -> bool:
    """Set up Telegram Earthquake Alert from a config entry."""
    try:
        monitored_dialogs = frozenset(
            str(dialog_id) for dialog_id in entry.data[CONF_DIALOGS]
        )
        client = TelegramClient(
            StringSession(entry.data[CONF_SESSION_STRING]),
            int(entry.data[CONF_API_ID]),
            entry.data[CONF_API_HASH],
        )
    except (KeyError, TypeError, ValueError) as err:
        raise ConfigEntryError("Invalid stored configuration") from err

    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise ConfigEntryAuthFailed("Telegram session is no longer authorized")
    except ConfigEntryAuthFailed:
        await _async_disconnect(client)
        raise
    except UnauthorizedError as err:
        await _async_disconnect(client)
        raise ConfigEntryAuthFailed("Telegram session is no longer authorized") from err
    except (OSError, RPCError) as err:
        await _async_disconnect(client)
        raise ConfigEntryNotReady("Unable to connect to Telegram") from err
    except Exception:
        await _async_disconnect(client)
        raise

    last_alert_times: dict[str, float] = {}

    async def message_handler(event: Any) -> None:
        """Forward matching Telegram messages to the Home Assistant event bus."""
        chat_id = str(event.chat_id)
        if chat_id not in monitored_dialogs:
            return

        raw_text = event.raw_text or ""
        if magnitude := find_magnitude(raw_text):
            now = monotonic()
            previous_alert_time = last_alert_times.get(chat_id)
            last_alert_times[chat_id] = now
            if (
                previous_alert_time is not None
                and now < previous_alert_time + ALERT_DEBOUNCE_SECONDS
            ):
                return

            hass.bus.async_fire(
                DOMAIN,
                {"magnitude": magnitude, "original_text": raw_text},
            )

    client.add_event_handler(message_handler, events.NewMessage(incoming=True))
    entry.runtime_data = TelegramEarthquakeAlertRuntimeData(client, message_handler)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TelegramEarthquakeAlertConfigEntry
) -> bool:
    """Unload a config entry."""
    runtime_data = entry.runtime_data
    runtime_data.client.remove_event_handler(runtime_data.message_handler)
    await _async_disconnect(runtime_data.client)
    return True
