from __future__ import annotations
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import User

from .const import (
    DOMAIN,
    CONF_API_ID,
    CONF_DIALOGS,
    CONF_API_HASH,
    CONF_PHONE_NUMBER,
    CONF_SESSION_STRING
)

MAX_WORD_DISTANCE = 3
PLATFORMS: list[Platform] = []

def find_magnitude(text):
        found_word = False
        word_distance = 0

        for word in text.split():
            if 'magnitudine' in word.lower():
                found_word = True
                continue

            if found_word:
                match = re.search(r"\d+[.,]\d+", word)
                if match and word_distance < MAX_WORD_DISTANCE:
                    magnitude = match.group()
                    return magnitude

                word_distance += 1

        return None

async def async_setup_entry(hass: HomeAssistant, entry: New_NameConfigEntry) -> bool:
    api_id = entry.options.get(CONF_API_ID, None) or entry.data.get(CONF_API_ID, None)
    api_hash = entry.options.get(CONF_API_HASH, None) or entry.data.get(CONF_API_HASH, None)
    phone_number = entry.options.get(CONF_PHONE_NUMBER, None) or entry.data.get(CONF_PHONE_NUMBER, None)
    dialogs = entry.options.get(CONF_DIALOGS, None) or entry.data.get(CONF_DIALOGS, None)
    session_string = entry.options.get(CONF_SESSION_STRING, None) or entry.data.get(CONF_SESSION_STRING, None)

    async def message_handler(event):
        if str(event.message.chat_id) in dialogs:
            raw_text = event.message.raw_text
            magnitude = find_magnitude(raw_text)
            if magnitude:
                hass.bus.async_fire(DOMAIN, {"magnitude": magnitude})

    instance = TelegramClient(
        StringSession(session_string),
        api_id,
        api_hash
    )
    await instance.connect()
    result = await instance.sign_in()

    if not isinstance(result, User):
        raise Exception("Invalid configuration or user session expired")

    instance.add_event_handler(
        message_handler,
        events.NewMessage(incoming=True)
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = instance

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        instance = hass.data[DOMAIN][entry.entry_id]
        await instance.disconnect()
    return unload_ok
