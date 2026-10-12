# Appliance Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/Valtteri-H/appliance-monitor)](https://github.com/Valtteri-H/appliance-monitor/releases)

Home Assistant -integraatio kodinkoneiden (pyykinpesukone, astianpesukone, kuivausrumpu) tilan ja syklien valvontaan tehomittausten (W) avulla.

Integraatio tunnistaa ohjelman vaiheet (lämmitys, linkous, liotus, valmis), suodattaa tehonvaihtelut ja arvioi käytetyn ohjelman sekä jäljellä olevan ajan tehodatan pohjalta.

> **Huomautus:** Tämä projekti on 100 % vibekoodattu.

---

## Ominaisuudet

- **Tilakone:**
  - Erottaa liotus- ja taukovaiheet syklin valmistumisesta konfiguroidun viiveen perusteella.
  - Suodattaa lyhytkestoiset tehonmuutokset.
- **Tehoprofiilien analyysi:**
  - Tunnistaa lämmitysvaiheen energian ja keston perusteella tavoitelämpötilat (esim. 30 °C, 40 °C, 60 °C, 90 °C).
  - Tunnistaa linkousvaiheet ja moottorin kuormituksen.
  - Ennustaa ohjelman ja jäljellä olevan keston opittujen profiilien perusteella.
- **Interaktiiviset ilmoitukset:**
  - Lähettää syklin päätyttyä ilmoituksen (kesto, kWh) ja toimintopainikkeet ohjelman vahvistamiseen.
- **Virhemerkintöjen korjaus:**
  - Painike viimeisimmän syklin poistamiseen profiilista (`button.<laite>_forget_last`).
  - Palvelut profiilien poistoon (`appliance_monitor.delete_program`) ja historian nollaukseen (`appliance_monitor.clear_history`).
- **Käyttöliittymäkonfigurointi (Config Flow):**
  - Lisäys ja muokkaus suoraan Home Assistantin käyttöliittymästä ilman YAML-määrityksiä.
  - Tukee tehosensoreita eri integraatioista (ZHA, Zigbee2MQTT, Shelly, Tuya jne.).
  - Täysi monikielituki (suomi ja englanti).

---

## Entiteetit

| Entiteetti | Tyyppi | Kuvaus |
| :--- | :--- | :--- |
| `sensor.<laite>_status` | Sensori (enum) | Laitteen tila (`off`, `idle`, `running`, `paused`, `finished`) |
| `sensor.<laite>_phase` | Sensori (enum) | Syklin vaihe (`weighing`, `heating`, `rinsing`, `spinning`, `drying`) |
| `sensor.<laite>_program` | Sensori | Tunnistettu ohjelma ja arvioitu luotettavuus |
| `sensor.<laite>_remaining_time` | Sensori (duration) | Arvioitu jäljellä oleva aika (min) |
| `sensor.<laite>_cycle_duration` | Sensori (duration) | Syklin kesto (min) |
| `sensor.<laite>_cycle_energy` | Sensori (energy) | Syklin kulutus (kWh) |
| `binary_sensor.<laite>_running` | Binäärisensori | Käynnissäolotila (`on` kun aktiivinen tai tauolla) |
| `select.<laite>_program_select` | Valitsin | Ohjelman vahvistus ja opetus |
| `text.<laite>_program_text` | Teksti | Uuden ohjelman nimen syöttö ja opetus |
| `button.<laite>_reset` | Painike | Kuittaa valmiustilaan |
| `button.<laite>_forget_last` | Painike | Poistaa edellisen syklin tiedot profiilista |

---

## Asennus

### HACS
1. Avaa Home Assistantissa **HACS** -> **Integrations**.
2. Valitse valikosta **Custom repositories**.
3. Lisää osoite `https://github.com/Valtteri-H/appliance-monitor` ja kategoriaksi **Integration**.
4. Lataa integraatio ja käynnistä Home Assistant uudelleen.
5. Lisää laite valikosta **Asetukset** -> **Laitteet ja palvelut** -> **Lisää integraatio** -> **Appliance Monitor**.

---

# English Documentation

Home Assistant integration for monitoring washing machines, dishwashers, and dryers using power measurements (W).

The integration detects cycle phases (heating, spinning, soaking, finished), filters power fluctuations, and estimates the active program and remaining time based on power signature data.

> **Note:** This project is 100% vibe-coded.

---

## Features

- **State Machine:**
  - Separates soaking pauses from cycle completion using a configurable delay.
  - Filters out transient power spikes.
- **Power Signature Engine:**
  - Identifies target temperatures based on heating phase energy and duration (e.g. 30 °C, 40 °C, 60 °C, 90 °C).
  - Detects spinning stages and motor load.
  - Predicts active program and remaining time from learned profiles.
- **Actionable Notifications:**
  - Sends a completion notification (duration, kWh) with action buttons to confirm the program.
- **Correction and Profile Management:**
  - Button entity to remove the previous cycle from learned profiles (`button.<appliance>_forget_last`).
  - Services to delete entire program profiles (`appliance_monitor.delete_program`) or clear history (`appliance_monitor.clear_history`).
- **UI Configuration (Config Flow):**
  - Set up and configure via Home Assistant UI without YAML editing.
  - Compatible with power sensors from any integration (ZHA, Zigbee2MQTT, Shelly, Tuya, etc.).
  - Full localization support for Finnish and English.

---

## Entities

| Entity | Type | Description |
| :--- | :--- | :--- |
| `sensor.<appliance>_status` | Sensor (enum) | Appliance state (`off`, `idle`, `running`, `paused`, `finished`) |
| `sensor.<appliance>_phase` | Sensor (enum) | Cycle phase (`weighing`, `heating`, `rinsing`, `spinning`, `drying`) |
| `sensor.<appliance>_program` | Sensor | Predicted program and confidence |
| `sensor.<appliance>_remaining_time` | Sensor (duration) | Estimated remaining duration (min) |
| `sensor.<appliance>_cycle_duration` | Sensor (duration) | Cycle duration (min) |
| `sensor.<appliance>_cycle_energy` | Sensor (energy) | Cycle energy consumption (kWh) |
| `binary_sensor.<appliance>_running` | Binary sensor | Activity state (`on` when running or paused) |
| `select.<appliance>_program_select` | Select | Program verification and learning selector |
| `text.<appliance>_program_text` | Text | Custom program name input and learning |
| `button.<appliance>_reset` | Button | Reset state to idle |
| `button.<appliance>_forget_last` | Button | Delete last cycle sample from profile |

---

## Installation

### HACS
1. Open Home Assistant and navigate to **HACS** -> **Integrations**.
2. Select **Custom repositories** from the menu.
3. Add `https://github.com/Valtteri-H/appliance-monitor` with category **Integration**.
4. Download the integration and restart Home Assistant.
5. Go to **Settings** -> **Devices & Services** -> **Add Integration** and search for **Appliance Monitor**.
