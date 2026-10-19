"""Config flow for Telegram Earthquake Alert."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_USER,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeEmptyError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    RPCError,
    SendCodeUnavailableError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession
from telethon.tl.types import User

from .const import (
    CONF_API_HASH,
    CONF_API_ID,
    CONF_DIALOGS,
    CONF_PHONE_NUMBER,
    CONF_SESSION_STRING,
    CONF_VERIFICATION_CODE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_DEFAULT_DIALOG_TITLE_PREFIX = "INFP alerte cutremur"
_PASSWORD_SELECTOR = TextSelector(
    TextSelectorConfig(
        type=TextSelectorType.PASSWORD,
        autocomplete="current-password",
    )
)
_API_ID_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT))
_SECRET_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
_CODE_SELECTOR = TextSelector(
    TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="one-time-code")
)
_PHONE_SELECTOR = TextSelector(
    TextSelectorConfig(type=TextSelectorType.TEL, autocomplete="tel")
)


def _dialogs_schema(
    dialogs: dict[str, str], default: list[str] | None = None
) -> vol.Schema:
    """Build a dialog multi-select schema."""
    return vol.Schema(
        {
            vol.Required(CONF_DIALOGS, default=default or []): vol.All(
                cv.multi_select(dialogs), vol.Length(min=1)
            )
        }
    )


class TelegramEarthquakeAlertConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Telegram Earthquake Alert."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize per-flow state."""
        self._api_id: int | None = None
        self._api_hash: str | None = None
        self._phone_number: str | None = None
        self._session_string: str | None = None
        self._telegram_user_id: int | None = None
        self._client: TelegramClient | None = None
        self._dialogs: dict[str, str] = {}

    async def _async_disconnect(self) -> None:
        """Disconnect the temporary config-flow client."""
        if self._client is None:
            return
        try:
            await self._client.disconnect()
        except Exception:
            _LOGGER.debug("Error disconnecting config-flow client", exc_info=True)
        finally:
            self._client = None

    async def _async_credentials_step(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
        defaults: Mapping[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Collect credentials and request a Telegram login code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_hash = user_input[CONF_API_HASH]
            self._phone_number = user_input[CONF_PHONE_NUMBER].strip()
            await self._async_disconnect()

            try:
                self._api_id = int(user_input[CONF_API_ID])
                if self._api_id < 1:
                    raise ValueError
            except (TypeError, ValueError):
                errors[CONF_API_ID] = "api_id_invalid"

            if not errors:
                try:
                    self._client = TelegramClient(
                        StringSession(), self._api_id, self._api_hash
                    )
                    await self._client.connect()
                    await self._client.send_code_request(self._phone_number)
                except ApiIdInvalidError:
                    errors["base"] = "api_id_invalid"
                except PhoneNumberInvalidError:
                    errors[CONF_PHONE_NUMBER] = "phone_number_invalid"
                except (FloodWaitError, SendCodeUnavailableError):
                    errors["base"] = "rate_limited"
                except (OSError, RPCError):
                    _LOGGER.exception("Unable to request a Telegram verification code")
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception(
                        "Unexpected error requesting a Telegram verification code"
                    )
                    errors["base"] = "unknown"

            if not errors:
                return await self.async_step_verification_code()
            await self._async_disconnect()

        schema = vol.Schema(
            {
                vol.Required(CONF_API_ID): _API_ID_SELECTOR,
                vol.Required(CONF_API_HASH): _SECRET_SELECTOR,
                vol.Required(CONF_PHONE_NUMBER): _PHONE_SELECTOR,
            }
        )
        if defaults:
            schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial credentials step."""
        return await self._async_credentials_step("user", user_input)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication for an expired Telegram session."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect credentials for reauthentication."""
        entry = self._get_reauth_entry()
        defaults = {
            CONF_API_ID: str(entry.data[CONF_API_ID]),
            CONF_PHONE_NUMBER: entry.data[CONF_PHONE_NUMBER],
        }
        return await self._async_credentials_step(
            "reauth_confirm", user_input, defaults
        )

    async def async_step_verification_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate the Telegram verification code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._client is not None
            assert self._phone_number is not None
            try:
                user = await self._client.sign_in(
                    phone=self._phone_number,
                    code=user_input[CONF_VERIFICATION_CODE].strip(),
                )
            except SessionPasswordNeededError:
                return await self.async_step_password()
            except (PhoneCodeEmptyError, PhoneCodeInvalidError):
                errors[CONF_VERIFICATION_CODE] = "invalid_verification_code"
            except PhoneCodeExpiredError:
                await self._async_disconnect()
                return self.async_abort(reason="verification_code_expired")
            except FloodWaitError:
                errors["base"] = "rate_limited"
            except (OSError, RPCError):
                _LOGGER.exception("Unable to verify the Telegram login code")
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error verifying the Telegram login code")
                errors["base"] = "unknown"
            else:
                return await self._async_login_complete(user)

        return self.async_show_form(
            step_id="verification_code",
            data_schema=vol.Schema(
                {vol.Required(CONF_VERIFICATION_CODE): _CODE_SELECTOR}
            ),
            errors=errors,
        )

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate the Telegram two-factor authentication password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._client is not None
            try:
                user = await self._client.sign_in(password=user_input[CONF_PASSWORD])
            except PasswordHashInvalidError:
                errors[CONF_PASSWORD] = "invalid_password"
            except FloodWaitError:
                errors["base"] = "rate_limited"
            except (OSError, RPCError):
                _LOGGER.exception("Unable to verify the Telegram password")
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error verifying the Telegram password")
                errors["base"] = "unknown"
            else:
                return await self._async_login_complete(user)

        return self.async_show_form(
            step_id="password",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): _PASSWORD_SELECTOR}),
            errors=errors,
        )

    async def _async_login_complete(self, user: User) -> ConfigFlowResult:
        """Store the authenticated session and continue to dialog selection."""
        if not isinstance(user, User):
            _LOGGER.error(
                "Telegram returned an unexpected login result: %s", type(user)
            )
            await self._async_disconnect()
            return self.async_abort(reason="unknown")

        assert self._client is not None
        self._telegram_user_id = user.id
        self._session_string = self._client.session.save()

        try:
            dialogs = await self._client.get_dialogs()
        except (OSError, RPCError):
            _LOGGER.exception("Unable to load Telegram dialogs")
            await self._async_disconnect()
            return self.async_abort(reason="cannot_connect")
        except Exception:
            _LOGGER.exception("Unexpected error loading Telegram dialogs")
            await self._async_disconnect()
            return self.async_abort(reason="unknown")

        self._dialogs = {
            str(dialog.id): title.strip()
            for dialog in dialogs
            if (title := getattr(dialog, "title", None)) and title.strip()
        }
        self._dialogs = dict(
            sorted(self._dialogs.items(), key=lambda item: item[1].casefold())
        )

        if not self._dialogs:
            await self._async_disconnect()
            return self.async_abort(reason="no_dialogs")

        return await self.async_step_select_dialogs()

    async def async_step_select_dialogs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the Telegram conversations to monitor."""
        default_dialogs: list[str] = []
        if self.source == SOURCE_REAUTH:
            default_dialogs = list(self._get_reauth_entry().data.get(CONF_DIALOGS, []))
        elif self.source == SOURCE_USER:
            default_dialogs = [
                dialog_id
                for dialog_id, title in self._dialogs.items()
                if title.startswith(_DEFAULT_DIALOG_TITLE_PREFIX)
            ]

        if user_input is None:
            return self.async_show_form(
                step_id="select_dialogs",
                data_schema=_dialogs_schema(self._dialogs, default_dialogs),
            )

        assert self._api_id is not None
        assert self._api_hash is not None
        assert self._phone_number is not None
        assert self._session_string is not None
        assert self._telegram_user_id is not None

        data = {
            CONF_API_ID: self._api_id,
            CONF_API_HASH: self._api_hash,
            CONF_PHONE_NUMBER: self._phone_number,
            CONF_SESSION_STRING: self._session_string,
            CONF_DIALOGS: user_input[CONF_DIALOGS],
        }
        await self._async_disconnect()

        if self.source == SOURCE_REAUTH:
            entry = self._get_reauth_entry()
            expected_user_id = entry.unique_id
            actual_user_id = str(self._telegram_user_id)
            if expected_user_id is not None and expected_user_id != actual_user_id:
                return self.async_abort(reason="reauth_account_mismatch")
            return self.async_update_reload_and_abort(
                entry,
                unique_id=actual_user_id,
                data_updates=data,
            )

        await self.async_set_unique_id(str(self._telegram_user_id))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=self._phone_number, data=data)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the Telegram conversations being monitored."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            return self.async_update_reload_and_abort(
                entry,
                data_updates={CONF_DIALOGS: user_input[CONF_DIALOGS]},
            )

        runtime_data = getattr(entry, "runtime_data", None)
        if runtime_data is None:
            return self.async_abort(reason="cannot_connect")

        try:
            dialogs = await runtime_data.client.get_dialogs()
        except (OSError, RPCError):
            _LOGGER.exception("Unable to load Telegram dialogs for reconfiguration")
            return self.async_abort(reason="cannot_connect")
        except Exception:
            _LOGGER.exception(
                "Unexpected error loading Telegram dialogs for reconfiguration"
            )
            return self.async_abort(reason="unknown")

        dialogs_map = {
            str(dialog.id): title.strip()
            for dialog in dialogs
            if (title := getattr(dialog, "title", None)) and title.strip()
        }
        dialogs_map = dict(
            sorted(dialogs_map.items(), key=lambda item: item[1].casefold())
        )
        if not dialogs_map:
            return self.async_abort(reason="no_dialogs")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_dialogs_schema(
                dialogs_map, list(entry.data.get(CONF_DIALOGS, []))
            ),
        )
