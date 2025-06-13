import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client
import re
import logging
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_REFRESH_RATE

_LOGGER = logging.getLogger(__name__)

class UtilitaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Utilita."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            refresh_rate = user_input[CONF_REFRESH_RATE]

            try:
                session = aiohttp_client.async_get_clientsession(self.hass)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
                async with session.get("https://my.utilita.co.uk/login", timeout=10, headers=headers, allow_redirects=True) as response:
                    if response.status != 200:
                        _LOGGER.error(f"Failed to load login page: HTTP {response.status}, URL: {response.url}")
                        raise Exception(f"Failed to load login page: HTTP {response.status}")
                    login_page = await response.text()
                    _LOGGER.debug(f"Login page URL: {response.url}, Headers: {response.headers}")
                    match = re.search(r'<input type="hidden" name="_token" value="([^"]+)"', login_page)
                    if not match:
                        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page, re.IGNORECASE)
                    if not match:
                        snippet = login_page[:1000]
                        _LOGGER.error(f"CSRF token not found in config flow. Login page snippet: {snippet}")
                        raise Exception("CSRF token not found")
                    token = match.group(1)
                    _LOGGER.debug(f"CSRF token found in config flow: {token[:10]}...")
                async with session.post(
                    "https://my.utilita.co.uk/login",
                    data={"_token": token, "email": email, "password": password, "remember": "on"},
                    timeout=10,
                    headers={
                        "User-Agent": headers["User-Agent"],
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Referer": "https://my.utilita.co.uk/login",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    }
                ) as response:
                    if response.status != 200 or "login" in str(response.url):
                        _LOGGER.error(f"Login failed in config flow: HTTP {response.status}, URL: {response.url}")
                        raise Exception("Invalid credentials or redirect")
                return self.async_create_entry(
                    title="Utilita Energy",
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_REFRESH_RATE: refresh_rate,
                    },
                )
            except Exception as err:
                _LOGGER.error(f"Config flow error: {err}")
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_REFRESH_RATE, default=3600): vol.All(
                        vol.Coerce(int), vol.Range(min=300)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UtilitaOptionsFlow(config_entry)

class UtilitaOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry
        _LOGGER.debug(f"Initializing options flow for entry: {config_entry.entry_id}")

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            _LOGGER.debug(f"Updating options with refresh_rate: {user_input[CONF_REFRESH_RATE]} for entry: {self.config_entry.entry_id}")
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REFRESH_RATE,
                        default=self.config_entry.options.get(CONF_REFRESH_RATE, self.config_entry.data.get(CONF_REFRESH_RATE, 3600)),
                    ): vol.All(vol.Coerce(int), vol.Range(min=300)),
                }
            ),
        )