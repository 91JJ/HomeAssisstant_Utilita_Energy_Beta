from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, EntityCategory
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import re
from .const import DOMAIN
import logging
from decimal import Decimal, ROUND_HALF_UP

_LOGGER = logging.getLogger(__name__)

def strip_html(text):
    """Remove HTML tags and normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("\xa0", " ").strip()

def format_amount(pence):
    """Convert pence to formatted pounds with commas and pound sign."""
    pounds = Decimal(pence) / Decimal('100')
    return f"£{pounds.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"

class UtilitaAccountSensor(CoordinatorEntity, SensorEntity):
    """Representation of the Utilita account sensor."""

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_icon = "mdi:account-details"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"utilita_{entry_id}")},
            name="Utilita Energy",
            manufacturer="Utilita",
            model="Energy Monitor",
        )

    @property
    def name(self):
        return "Account"

    @property
    def unique_id(self):
        return f"utilita_{self._entry_id}_account"

    @property
    def state(self):
        try:
            return self.coordinator.data["user_data"]["customer_id"]
        except (KeyError, TypeError) as err:
            _LOGGER.error(f"Error parsing customer ID: {err}")
            return None

    @property
    def extra_state_attributes(self):
        try:
            user_data = self.coordinator.data["user_data"]
            premises = user_data.get("premises", [])
            if not premises:
                _LOGGER.warning("No premises found in user_data")
                return {}
            attrs = {
                "address": premises[0].get("addr_full"),
                "premises_id": str(premises[0].get("premises_id", "")).replace(",", ""),
            }
            return attrs
        except (KeyError, TypeError) as err:
            _LOGGER.error(f"Error parsing account attributes: {err}")
            return {}

    @property
    def available(self):
        return self.coordinator.last_update_success

class UtilitaBalanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Utilita balance sensor."""

    def __init__(self, coordinator, entry_id, supply_type, name):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._supply_type = supply_type
        self._name = name
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:fire" if supply_type == "gas" else "mdi:lightning-bolt-outline"
        self._attr_suggested_display_precision = 2
        self._attr_unit_of_measurement = "£"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"utilita_{entry_id}")},
            name="Utilita Energy",
            manufacturer="Utilita",
            model="Energy Monitor",
        )

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"utilita_{self._entry_id}_{self._supply_type}_balance"

    @property
    def state(self):
        try:
            data = self.coordinator.data["balance"]["data"]["supplies"]
            for supply in data:
                if supply.get("type") == self._supply_type:
                    value = Decimal(str(supply["balance"]["money"])) / Decimal('100')
                    return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.error(f"Error parsing balance for {self._supply_type}: {err}")
        return None

    @property
    def extra_state_attributes(self):
        try:
            data = self.coordinator.data["balance"]["data"]["supplies"]
            for supply in data:
                if supply.get("type") == self._supply_type:
                    messages = [msg["text"] for msg in supply["balance"].get("messages", [])]
                    attrs = {
                        "supply_id": supply.get("supply_id"),
                        "payment_mode": supply.get("payment_mode"),
                        "zero_time": supply["balance"].get("zero_time"),
                        "duration_remaining": strip_html(supply["balance"].get("duration")),
                        "updated": supply["balance"].get("updated"),
                        "emergency_credit_status": supply["emergency_credit"].get("status", "Unknown"),
                        "debt_money": supply["debt"].get("money", 0),
                        "debt_recovery_rate": supply["debt"].get("debt_recovery_rate", 0),
                        "messages": messages,
                    }
                    return attrs
        except (KeyError, TypeError) as err:
            _LOGGER.error(f"Error parsing balance attributes for {self._supply_type}: {err}")
        return {}

    @property
    def available(self):
        return self.coordinator.last_update_success

class UtilitaUsageSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Utilita usage sensor."""

    def __init__(self, coordinator, entry_id, supply_type, name, period):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._supply_type = supply_type
        self._name = name
        self._period = period
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:fire" if supply_type == "gas" else "mdi:lightning-bolt-outline"
        self._attr_suggested_display_precision = 3
        self._attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"utilita_{entry_id}")},
            name="Utilita Energy",
            manufacturer="Utilita",
            model="Energy Monitor",
        )

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"utilita_{self._entry_id}_{self._supply_type}_{self._period}_usage"

    @property
    def state(self):
        try:
            data = self.coordinator.data["usage"]["data"]["data"]
            for supply in data:
                if supply.get("type") == self._supply_type:
                    if self._period == "daily":
                        value = Decimal(str(supply["usage"][-1]["kwh"])) if supply.get("usage") else None
                        return float(value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)) if value else None
                    elif self._period == "weekly":
                        value = sum(Decimal(str(u["kwh"])) for u in supply.get("usage", [])[-7:])
                        return float(value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
                    elif self._period == "monthly":
                        value = Decimal(str(supply["monthly_kwh"]))
                        return float(value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
                    elif self._period == "yearly":
                        value = Decimal(str(supply["yearly_kwh"]))
                        return float(value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
        except (KeyError, TypeError, IndexError, ValueError) as err:
            _LOGGER.error(f"Error parsing usage for {self._supply_type} ({self._period}): {err}")
        return None

    @property
    def extra_state_attributes(self):
        try:
            data = self.coordinator.data["usage"]["data"]["data"]
            for supply in data:
                if supply.get("type") == self._supply_type:
                    attrs = {
                        "supply_id": supply.get("supply_id"),
                    }
                    # Fetch meter_units from user_data supplies
                    user_data_supplies = self.coordinator.data["user_data"]["premises"][0]["supplies"]
                    for user_supply in user_data_supplies:
                        if user_supply.get("span") == supply.get("supply_id"):
                            meter_units = user_supply.get("meter", {}).get("units")
                            attrs["meter_units"] = meter_units
                            break
                    if self._period == "daily":
                        if supply.get("usage"):
                            last_usage = supply["usage"][-1]
                            attrs.update({
                                "last_updated": last_usage.get("date"),
                                "kwh": float(Decimal(str(last_usage["kwh"])).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)),
                                "pence": last_usage.get("pence"),
                                "avg_temp": f"{last_usage.get('avg_temperature_c')}°C",
                            })
                        else:
                            attrs.update({
                                "last_updated": None,
                                "kwh": None,
                                "pence": None,
                                "avg_temp": None,
                            })
                    elif self._period == "weekly":
                        weekly_usage = [
                            {
                                "date": u.get("date"),
                                "kwh": float(Decimal(str(u["kwh"])).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)),
                                "pence": u.get("pence"),
                                "avg_temp": f"{u.get('avg_temperature_c')}°C",
                            }
                            for u in supply.get("usage", [])[-7:]
                        ]
                        attrs["weekly_usage"] = weekly_usage
                        weekly_cost = sum(Decimal(str(u.get("pence", 0))) for u in supply.get("usage", [])[-7:])
                        attrs["weekly_cost"] = format_amount(weekly_cost)
                    elif self._period == "monthly":
                        monthly_cost = supply.get("monthly_cost")
                        if monthly_cost is not None:
                            attrs["monthly_cost"] = format_amount(monthly_cost)
                    elif self._period == "yearly":
                        yearly_cost = supply.get("yearly_cost")
                        if yearly_cost is not None:
                            attrs["yearly_cost"] = format_amount(yearly_cost)
                    return attrs
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.error(f"Error parsing usage attributes for {self._supply_type} ({self._period}): {err}")
        return {}

    @property
    def available(self):
        return self.coordinator.last_update_success

class UtilitaTariffSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Utilita tariff sensor."""

    def __init__(self, coordinator, entry_id, supply_type, name):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._supply_type = supply_type
        self._name = name
        self._attr_icon = "mdi:fire" if supply_type == "gas" else "mdi:lightning-bolt-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"utilita_{entry_id}")},
            name="Utilita Energy",
            manufacturer="Utilita",
            model="Energy Monitor",
        )

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"utilita_{self._entry_id}_{self._supply_type}_tariff"

    @property
    def state(self):
        try:
            data = self.coordinator.data["user_data"]["premises"][0]["supplies"]
            for supply in data:
                if supply.get("type") == self._supply_type:
                    return supply.get("tariff_name")
        except (KeyError, TypeError, IndexError) as err:
            _LOGGER.error(f"Error parsing tariff for {self._supply_type}: {err}")
        return None

    @property
    def extra_state_attributes(self):
        try:
            data = self.coordinator.data["user_data"]["premises"][0]["supplies"]
            for supply in data:
                if supply.get("type") == self._supply_type:
                    description = strip_html(supply.get("tariff_description", ""))
                    first_rate_kwh = None
                    match = re.search(r"First (\d+\.?\d*) kWh", description, re.IGNORECASE)
                    if match:
                        first_rate_kwh = float(match.group(1))
                    attrs = {
                        "region_name": supply.get("region_name"),
                        "first_rate_kwh": first_rate_kwh,
                        "rate1": f"{round(float(supply['rate1']), 2)}p" if supply.get("rate1") else None,
                        "rate2": f"{round(float(supply['rate2']), 2)}p" if supply.get("rate2") else None,
                        "span": supply.get("span"),
                        "pan": supply.get("pan"),
                        "meter_id": supply.get("meter", {}).get("id"),
                        "meter_units": supply.get("meter", {}).get("units"),
                        "supply_start_date": supply.get("supply_start_date"),
                    }
                    if self._supply_type == "elec":
                        mpan = supply.get("mpan", {})
                        top_line = mpan.get("top_line", {})
                        core = mpan.get("core", {})
                        attrs["mpan"] = f"{top_line.get('pc', '')} {top_line.get('mtc', '')} {top_line.get('llfc', '')} {core.get('did', '')} {core.get('ui', '')} {core.get('cd', '')}".strip()
                    usage_data = self.coordinator.data["usage"]["data"]["data"]
                    for usage_supply in usage_data:
                        if usage_supply.get("supply_id") == supply.get("span"):
                            attrs["is_smart_meter"] = usage_supply.get("is_smart_meter")
                            attrs["smets"] = usage_supply.get("smets")
                            break
                    else:
                        _LOGGER.warning(f"No matching usage data found for supply {supply.get('span')}")
                    attrs["tariff_description"] = description
                    return attrs
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.error(f"Error parsing tariff attributes for {self._supply_type}: {err}")
        return {}

    @property
    def available(self):
        return self.coordinator.last_update_success

class UtilitaCurrentRateSensor(CoordinatorEntity, SensorEntity):
    """Representation of the current rate sensor based on daily usage."""

    def __init__(self, coordinator, entry_id, supply_type, name):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._supply_type = supply_type
        self._name = name
        self._attr_icon = "mdi:fire-circle" if supply_type == "gas" else "mdi:lightning-bolt-circle"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"utilita_{entry_id}")},
            name="Utilita Energy",
            manufacturer="Utilita",
            model="Energy Monitor",
        )

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"utilita_{self._entry_id}_{self._supply_type}_current_rate"

    @property
    def state(self):
        try:
            usage_data = self.coordinator.data["usage"]["data"]["data"]
            for supply in usage_data:
                if supply.get("type") == self._supply_type:
                    daily_usage = Decimal(str(supply["usage"][-1]["kwh"])) if supply.get("usage") else Decimal('0')

            tariff_data = self.coordinator.data["user_data"]["premises"][0]["supplies"]
            for supply in tariff_data:
                if supply.get("type") == self._supply_type:
                    description = strip_html(supply.get("tariff_description", ""))
                    match = re.search(r"First (\d+\.?\d*) kWh", description, re.IGNORECASE)
                    first_rate_kwh = Decimal(str(match.group(1))) if match else Decimal('0')
                    rate1 = Decimal(str(supply.get("rate1", 0)))
                    rate2 = Decimal(str(supply.get("rate2", 0)))

            if daily_usage <= first_rate_kwh:
                return f"{float(rate1.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))}p"
            else:
                return f"{float(rate2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))}p"
        except (KeyError, TypeError, ValueError, IndexError) as err:
            _LOGGER.error(f"Error calculating current rate for {self._supply_type}: {err}")
        return None

    @property
    def extra_state_attributes(self):
        try:
            usage_data = self.coordinator.data["usage"]["data"]["data"]
            for supply in usage_data:
                if supply.get("type") == self._supply_type:
                    daily_usage = Decimal(str(supply["usage"][-1]["kwh"])) if supply.get("usage") else Decimal('0')

            tariff_data = self.coordinator.data["user_data"]["premises"][0]["supplies"]
            for supply in tariff_data:
                if supply.get("type") == self._supply_type:
                    description = strip_html(supply.get("tariff_description", ""))
                    match = re.search(r"First (\d+\.?\d*) kWh", description, re.IGNORECASE)
                    first_rate_kwh = Decimal(str(match.group(1))) if match else Decimal('0')
                    return {
                        "daily_usage_kwh": float(daily_usage.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)),
                        "first_rate_kwh": float(first_rate_kwh),
                        "rate1": f"{float(Decimal(str(supply['rate1'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))}p" if supply.get("rate1") else None,
                        "rate2": f"{float(Decimal(str(supply['rate2'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))}p" if supply.get("rate2") else None,
                    }
        except (KeyError, TypeError, ValueError, IndexError) as err:
            _LOGGER.error(f"Error fetching attributes for current rate {self._supply_type}: {err}")
        return {}

    @property
    def available(self):
        return self.coordinator.last_update_success

class UtilitaPaymentsSensor(CoordinatorEntity, SensorEntity):
    """Representation of the Utilita payments sensor."""

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_icon = "mdi:currency-gbp"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"utilita_{entry_id}")},
            name="Utilita Energy",
            manufacturer="Utilita",
            model="Energy Monitor",
        )

    @property
    def name(self):
        return "Payments"

    @property
    def unique_id(self):
        return f"utilita_{self._entry_id}_payments"

    @property
    def state(self):
        try:
            payments = self.coordinator.data["payments"]["payments"]
            return len(payments)
        except (KeyError, TypeError) as err:
            _LOGGER.error(f"Error parsing payments list: {err}")
            return None

    @property
    def extra_state_attributes(self):
        try:
            payments = self.coordinator.data["payments"]["payments"]
            grouped_payments = {}
            for payment in payments:
                date = payment["issuetime"].split("T")[0]
                if date not in grouped_payments:
                    grouped_payments[date] = []
                payment_details = {
                    "type": payment["type"],
                    "amount": format_amount(payment["metercreditamount"]),
                    "debt_deducted": format_amount(payment.get("debtdeducted", 0)),
                    "debt_recovery_rate": payment.get("debtrecoveryrate", 0),
                    "transaction_amount": format_amount(payment["transactionamount"]),
                    "full_description": payment["full_description"].strip(),
                    "issuetime": payment["issuetime"],
                }
                grouped_payments[date].append(payment_details)
            return grouped_payments
        except (KeyError, TypeError) as err:
            _LOGGER.error(f"Error parsing payments attributes: {err}")
            return {}

    @property
    def available(self):
        return self.coordinator.last_update_success

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Utilita sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    entry_id = config_entry.entry_id
    sensors = []

    sensors.extend([
        UtilitaAccountSensor(coordinator, entry_id),
        UtilitaBalanceSensor(coordinator, entry_id, "gas", "Gas Balance"),
        UtilitaBalanceSensor(coordinator, entry_id, "elec", "Electricity Balance"),
        UtilitaUsageSensor(coordinator, entry_id, "gas", "Daily Gas Usage", "daily"),
        UtilitaUsageSensor(coordinator, entry_id, "elec", "Daily Electricity Usage", "daily"),
        UtilitaUsageSensor(coordinator, entry_id, "gas", "Monthly Gas Usage", "monthly"),
        UtilitaUsageSensor(coordinator, entry_id, "elec", "Monthly Electricity Usage", "monthly"),
        UtilitaUsageSensor(coordinator, entry_id, "gas", "Weekly Gas Usage", "weekly"),
        UtilitaUsageSensor(coordinator, entry_id, "elec", "Weekly Electricity Usage", "weekly"),
        UtilitaUsageSensor(coordinator, entry_id, "gas", "Yearly Gas Usage", "yearly"),
        UtilitaUsageSensor(coordinator, entry_id, "elec", "Yearly Electricity Usage", "yearly"),
        UtilitaTariffSensor(coordinator, entry_id, "gas", "Gas Tariff"),
        UtilitaTariffSensor(coordinator, entry_id, "elec", "Electricity Tariff"),
        UtilitaCurrentRateSensor(coordinator, entry_id, "gas", "Current Gas Rate"),
        UtilitaCurrentRateSensor(coordinator, entry_id, "elec", "Current Electric Rate"),
        UtilitaPaymentsSensor(coordinator, entry_id),
    ])

    async_add_entities(sensors)