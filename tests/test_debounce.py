"""Test the Telegram handler with controlled time and mocked dependencies."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch


def load_integration():
    """Load the integration without requiring Home Assistant or Telegram."""
    dependencies = {
        "homeassistant": {},
        "homeassistant.config_entries": {"ConfigEntry": Mock()},
        "homeassistant.core": {"HomeAssistant": Mock()},
        "homeassistant.exceptions": {
            name: type(name, (Exception,), {})
            for name in (
                "ConfigEntryAuthFailed", "ConfigEntryError", "ConfigEntryNotReady"
            )
        },
        "telethon": {"TelegramClient": Mock(), "events": Mock()},
        "telethon.errors": {
            name: type(name, (Exception,), {})
            for name in ("RPCError", "UnauthorizedError")
        },
        "telethon.sessions": {"StringSession": Mock()},
    }
    modules = {}
    for name, attributes in dependencies.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module

    path = (
        Path(__file__).parents[1]
        / "custom_components" / "telegram_earthquake_alert" / "__init__.py"
    )
    spec = importlib.util.spec_from_file_location("debounce_test_integration", path)
    assert spec is not None and spec.loader is not None
    integration = importlib.util.module_from_spec(spec)
    modules[spec.name] = integration
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(integration)
    return integration


class AlertDebounceTest(unittest.IsolatedAsyncioTestCase):
    """Exercise debounce through the registered message handler."""

    async def asyncSetUp(self) -> None:
        self.integration = load_integration()
        self.client = Mock()
        self.client.connect = AsyncMock()
        self.client.is_user_authorized = AsyncMock(return_value=True)
        self.client.disconnect = AsyncMock()
        self.integration.TelegramClient.return_value = self.client
        self.hass = SimpleNamespace(bus=SimpleNamespace(async_fire=Mock()))
        self.entry = SimpleNamespace(data={
            "api_id": 123, "api_hash": "test", "session_string": "test",
            "dialogs": [1, 2],
        })
        self.clock = Mock(return_value=0.0)
        self.integration.monotonic = self.clock
        await self.integration.async_setup_entry(self.hass, self.entry)

    async def send(self, at: float, text="magnitudinea Mw=5.1", chat_id=1):
        self.clock.return_value = at
        await self.entry.runtime_data.message_handler(
            SimpleNamespace(chat_id=chat_id, raw_text=text)
        )

    async def test_first_alert_is_immediate_and_preserves_payload(self) -> None:
        text = "Cutremur cu magnitudinea Mw=5.1"
        await self.send(0, text)
        self.hass.bus.async_fire.assert_called_once_with(
            "telegram_earthquake_alert", {"magnitude": "5.1", "original_text": text}
        )

    async def test_burst_extends_quiet_period_and_accepts_exact_boundary(self) -> None:
        await self.send(0)
        await self.send(20)
        await self.send(49.999)
        self.assertEqual(self.hass.bus.async_fire.call_count, 1)
        await self.send(79.999)
        self.assertEqual(self.hass.bus.async_fire.call_count, 2)

    async def test_alert_after_quiet_period_is_accepted(self) -> None:
        await self.send(0)
        await self.send(31)
        self.assertEqual(self.hass.bus.async_fire.call_count, 2)

    async def test_chats_are_independent(self) -> None:
        await self.send(0, chat_id=1)
        await self.send(1, chat_id=2)
        await self.send(2, chat_id=1)
        self.assertEqual(self.hass.bus.async_fire.call_count, 2)

    async def test_invalid_messages_do_not_extend_quiet_period(self) -> None:
        await self.send(0)
        for text in ("unrelated message", "magnitudine necunoscută", "", None):
            await self.send(29, text)
        await self.send(30)
        self.assertEqual(self.hass.bus.async_fire.call_count, 2)

    async def test_unmonitored_chat_is_ignored(self) -> None:
        await self.send(0, chat_id=99)
        self.hass.bus.async_fire.assert_not_called()
        self.clock.assert_not_called()
        await self.send(1)
        self.hass.bus.async_fire.assert_called_once()

    async def test_magnitude_revision_is_suppressed_and_extends_quiet_period(self) -> None:
        await self.send(0)
        await self.send(10, "magnitudinea Mw=5.3")
        self.hass.bus.async_fire.assert_called_once_with(
            "telegram_earthquake_alert",
            {"magnitude": "5.1", "original_text": "magnitudinea Mw=5.1"},
        )
        await self.send(30)
        self.assertEqual(self.hass.bus.async_fire.call_count, 1)

    async def test_entries_have_independent_state(self) -> None:
        await self.send(0)
        other_entry = SimpleNamespace(data=dict(self.entry.data))
        await self.integration.async_setup_entry(self.hass, other_entry)
        self.clock.return_value = 1
        await other_entry.runtime_data.message_handler(
            SimpleNamespace(chat_id=1, raw_text="magnitudinea Mw=5.1")
        )
        self.assertEqual(self.hass.bus.async_fire.call_count, 2)

    async def test_reload_resets_debounce_state(self) -> None:
        await self.send(0)
        await self.integration.async_unload_entry(self.hass, self.entry)
        await self.integration.async_setup_entry(self.hass, self.entry)
        await self.send(1)
        self.assertEqual(self.hass.bus.async_fire.call_count, 2)


if __name__ == "__main__":
    unittest.main()
