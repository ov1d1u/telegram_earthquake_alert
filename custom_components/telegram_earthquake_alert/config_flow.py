"""Config flow for Alerta Cutremur integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import HomeAssistantError

from telethon import TelegramClient
from telethon.tl.types import User
from telethon.tl.types.auth import SentCode
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.errors.rpcerrorlist import (
    SendCodeUnavailableError,
    ApiIdInvalidError
)

from .const import (
    DOMAIN,
    CONF_API_ID,
    CONF_DIALOGS,
    CONF_API_HASH,
    CONF_PHONE_NUMBER,
    CONF_SESSION_STRING,
    CONF_VERIFICATION_CODE
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alerta Cutremur."""

    VERSION = 1

    name = "Telegram Earthquake Alert"
    api_id = None
    api_hash = None
    phone_number = None
    verification_code = None
    password = None
    session_string = None
    dialog_ids = []
    telegram_client = None

    async def _sign_in_and_get_next_step(self) -> ConfigFlowResult:
        try:
            result = await self.telegram_client.sign_in(
                self.phone_number,
                code=self.verification_code,
                password=self.password
            )
        except SendCodeUnavailableError:
            raise HomeAssistantError("invalid_verification_code")
        except SessionPasswordNeededError:
            return await self.async_step_password()
        except HomeAssistantError as e:
            raise HomeAssistantError(e)

        if isinstance(result, SentCode):
            return await self.async_step_verification_code()
        elif isinstance(result, User):
            self.session_string = self.telegram_client.session.save()
            return await self.async_step_select_dialogs()

        raise HomeAssistantError("unknown")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self.api_id = user_input[CONF_API_ID]
            self.api_hash = user_input[CONF_API_HASH]
            self.phone_number = user_input[CONF_PHONE_NUMBER]
            try:
                self.telegram_client = TelegramClient(
                    StringSession(),
                    user_input[CONF_API_ID],
                    user_input[CONF_API_HASH]
                )
                await self.telegram_client.connect()
                return await self._sign_in_and_get_next_step()
            except HomeAssistantError as e:
                errors["base"] = str(e)
            except ApiIdInvalidError as e:
                errors["base"] = "api_id_invalid"
            except Exception as e:
                _LOGGER.exception(e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_ID): str,
                    vol.Required(CONF_API_HASH): str,
                    vol.Required(CONF_PHONE_NUMBER): str
                }
            ),
            errors=errors
        )

    async def async_step_verification_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the verification code step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.verification_code = user_input[CONF_VERIFICATION_CODE]
            try:
                return await self._sign_in_and_get_next_step()
            except HomeAssistantError as e:
                errors["base"] = str(e)
            except Exception as e:
                _LOGGER.exception(e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="verification_code",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VERIFICATION_CODE): str
                }
            ),
            errors=errors
        )

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the password step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.password = user_input[CONF_PASSWORD]

            # Set verification_code to None as we're logging in
            # with a password, now
            self.verification_code = None

            try:
                return await self._sign_in_and_get_next_step()
            except HomeAssistantError as e:
                errors["base"] = str(e)
            except Exception as e:
                _LOGGER.exception(e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="password",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str
                }
            ),
            errors=errors
        )

    async def async_step_select_dialogs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the select chats step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.dialog_ids = user_input[CONF_DIALOGS]

            return self.async_create_entry(
                title=self.phone_number,
                data={
                    CONF_API_ID: self.api_id,
                    CONF_API_HASH: self.api_hash,
                    CONF_PHONE_NUMBER: self.phone_number,
                    CONF_SESSION_STRING: self.session_string,
                    CONF_DIALOGS: self.dialog_ids
                }
            )

        dialogs = await self.telegram_client.get_dialogs()
        dialogs_map = { str(d.id) : d.title for d in dialogs if d.title.strip() }
        dialogs_map = dict(sorted(dialogs_map.items(), key=lambda item: item[1].strip().lower()))

        return self.async_show_form(
            step_id="select_dialogs",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DIALOGS): cv.multi_select(dialogs_map)
                }
            ),
            errors=errors
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Add reconfigure step to allow to reconfigure a config entry."""
        errors: dict[str, str] = {}
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if user_input is not None:
            dialog_ids = user_input[CONF_DIALOGS]

            return self.async_update_reload_and_abort(
                config_entry,
                unique_id=config_entry.unique_id,
                data={**config_entry.data, **user_input},
                reason="reconfigure_successful"
            )

        instance = self.hass.data[DOMAIN][self.context["entry_id"]]
        dialogs = await instance.get_dialogs()
        dialogs_map = { str(d.id) : d.title for d in dialogs if d.title.strip() }
        dialogs_map = dict(sorted(dialogs_map.items(), key=lambda item: item[1].strip().lower()))
        current_dialog_ids = config_entry.data.get(CONF_DIALOGS, [])

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DIALOGS, default=current_dialog_ids): cv.multi_select(dialogs_map)
                }
            ),
            errors=errors
        )
