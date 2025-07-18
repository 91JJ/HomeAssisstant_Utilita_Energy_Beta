
![logo](https://github.com/user-attachments/assets/2f0704e1-80c1-4f1c-8116-b4d986156947)

# Utilita Energy Integration for Home Assistant

This integration allows Home Assistant to fetch energy usage, balance, tariff, and payment data from Utilita Energy accounts.  
A lot of the data is stored within the Attributes so may require other integrations to utilise the data if required.  


## Installation
1. ~~Install via Home Assistants Integrations (recommended) or~~
2. Manually copy the `custom_components/utilita` folder to your Home Assistant `custom_components/` directory.
3. Restart Home Assistant.
4. Go to **Settings > Devices & Services > Add Integration** and search for "Utilita Energy."
5. Enter your Utilita email, password, and desired refresh rate.  


## Configuration
- **Email**: Your Utilita account email.
- **Password**: Your Utilita account password.
- **Refresh Rate**: Data polling interval in seconds (minimum 300).  


## Sensors
### Sensors
- Daily Electricity Usage (_This has been noted to be days behind due to source data_)
- Daily Gas Usage (_This has been noted to be days behind due to source data_)
- Electricity Balance
- Gas Balance
- Monthly Electricity Usage
- Monthly Gas Usage
- Weekly Electricity Usage
- Weekly Gas Usage
- Yearly Electricity Usage
- Yearly Gas Usage

### Diagnostic
- Account
- Current Electric Rate (_This has been noted to be days behind due to source data_)
- Current Gas Rate (_This has been noted to be days behind due to source data_)
- Electricity Tariff
- Gas Tariff  

<br/>

## To-Do
- [x] Open Beta. :tada:
- [X] Create icon & publish to Brands. (Completed :tada: - https://github.com/home-assistant/brands/pull/7248#pullrequestreview-2967758252)
- [ ] Add Service Call to update sensors on request.
- [ ] Add to Home Assistant Integrations.

- [ ] Fix "Detected that custom integration 'utilita' sets option flow config_entry explicitly, which is deprecated at custom_components/utilita/config_flow.py, line 100: self.config_entry = config_entry. This will stop working in Home Assistant 2025.12, please report it to the author of the 'utilita' custom integration"


## Home Assisstant Feedback
Please leave any feedback, comments etc on Home Assistant Community...  
https://community.home-assistant.io/t/utilita-energy-uk-utility-sensors/901143

<br/> <br/>
> [!WARNING]
>  This integration has only been tested with Pay As You Go customers.

> [!CAUTION]
>  This integration isn't supported by Utilita Energy and the APIs could change at any time causing the sensors, or worse, the integration to fail.
