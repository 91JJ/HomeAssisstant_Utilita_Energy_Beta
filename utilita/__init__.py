from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import aiohttp_client
import re
import logging
from datetime import timedelta, date
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_REFRESH_RATE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Utilita from a config entry."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    refresh_rate = entry.options.get(CONF_REFRESH_RATE, entry.data.get(CONF_REFRESH_RATE, 3600))
    _LOGGER.debug(f"Setting up entry {entry.entry_id} with refresh_rate: {refresh_rate} seconds")

    async def async_update_data():
        """Fetch data from Utilita."""
        _LOGGER.debug(f"Starting data update for entry {entry.entry_id} at {date.today()} {timedelta(seconds=refresh_rate)}")
        try:
            session = aiohttp_client.async_get_clientsession(hass)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            async with session.get("https://my.utilita.co.uk/login", timeout=10, headers=headers, allow_redirects=True) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Failed to load login page: HTTP {response.status}, URL: {response.url}")
                login_page = await response.text()
                _LOGGER.debug(f"Login page URL: {response.url}, Headers: {response.headers}")
                match = re.search(r'<input type="hidden" name="_token" value="([^"]+)"', login_page)
                if not match:
                    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page, re.IGNORECASE)
                if not match:
                    snippet = login_page[:1000]
                    _LOGGER.error(f"CSRF token not found. Login page snippet: {snippet}")
                    raise UpdateFailed("CSRF token not found")
                token = match.group(1)
                _LOGGER.debug(f"CSRF token found: {token[:10]}...")
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
                    raise UpdateFailed(f"Login failed: HTTP {response.status}, URL: {response.url}")
            async with session.get("https://my.utilita.co.uk/json/balance", timeout=10, headers={
                "User-Agent": headers["User-Agent"],
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://my.utilita.co.uk/energy",
                "Connection": "keep-alive",
            }) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Failed to fetch balance: HTTP {response.status}")
                balance = await response.json()
            async with session.get(f"https://my.utilita.co.uk/json/usage?end_date={date.today()}", timeout=10, headers={
                "User-Agent": headers["User-Agent"],
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://my.utilita.co.uk/energy",
                "Connection": "keep-alive",
            }) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Failed to fetch usage: HTTP {response.status}")
                usage = await response.json()
            async with session.get("https://my.utilita.co.uk/user-data", timeout=10, headers={
                "User-Agent": headers["User-Agent"],
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://my.utilita.co.uk/energy",
                "Connection": "keep-alive",
            }) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Failed to fetch user data: HTTP {response.status}")
                user_data = await response.json()
            async with session.get("https://my.utilita.co.uk/json/payments?page=1&per_page=50", timeout=10, headers={
                "User-Agent": headers["User-Agent"],
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://my.utilita.co.uk/energy",
                "Connection": "keep-alive",
            }) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Failed to fetch payments: HTTP {response.status}")
                payments = await response.json()
            _LOGGER.debug(f"Data update completed successfully for entry {entry.entry_id}")
            return {"balance": balance, "usage": usage, "user_data": user_data, "payments": payments}
        except Exception as err:
            _LOGGER.error(f"Error fetching data for entry {entry.entry_id}: {err}")
            raise UpdateFailed(f"Error fetching data: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Utilita_{entry.entry_id}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=refresh_rate),
    )

    await coordinator.async_config_entry_first_refresh()
    if not coordinator.last_update_success:
        _LOGGER.error(f"Initial refresh failed for entry {entry.entry_id}")
        return False
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator, "config": entry}
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if await hass.config_entries.async_unload_platforms(entry, ["sensor"]):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False

async def async_options_updated(hass, entry):
    """Handle options update."""
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        if coordinator:
            new_refresh_rate = entry.options.get(CONF_REFRESH_RATE, 3600)
            coordinator.update_interval = timedelta(seconds=new_refresh_rate)
            await coordinator.async_request_refresh()
    return True