# Appliance Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/Valtteri-H/appliance-monitor)](https://github.com/Valtteri-H/appliance-monitor/releases)

Home Assistant -integraatio kodinkoneiden (pyykinpesukone, astianpesukone, kuivausrumpu) tilan ja syklien valvontaan tehomittausten (W) avulla.

Integraatio tunnistaa ohjelman vaiheet (lämmitys, linkous, kuivaus, liotus, valmis), suodattaa tehonvaihtelut ja arvioi käytetyn ohjelman sekä jäljellä olevan ajan tehodatan pohjalta.

> **Huomautus:** Tämä projekti on 100 % vibekoodattu.

---

## Ominaisuudet

- **Tilakone ja ajastettu varmistus:**
  - Erottaa liotus- ja taukovaiheet syklin valmistumisesta konfiguroidun viiveen ja tausta-ajastimen perusteella.
  - Suodattaa lyhytkestoiset tehonmuutokset sekä tehosensorin katkokset (`unavailable` / `unknown`).
  - Palauttaa käynnissä olevan pesusyklin tilan Home Assistantin uudelleenkäynnistyksen jälkeen.
- **Tehoprofiilien analyysi (EMA-oppiminen):**
  - Tunnistaa lämmitysvaiheen energian, keston, huipputehon ja linkouksen perusteella pesu- ja kuivausohjelmat (mukaan lukien kylmäpesut ja lämpöpumppukuivausrummut).
  - Mukautuu ajan myötä eksponentiaalisesti painotetulla liukuvalla keskiarvolla (EMA).
  - Ennustaa aktiivisen ohjelman ja jäljellä olevan keston opittujen profiilien perusteella.
- **Interaktiiviset ilmoitukset, hiljaiset tunnit ja muistutukset:**
  - Lähettää syklin päätyttyä ilmoituksen (kesto, kWh) ja toimintopainikkeet ohjelman vahvistamiseen.
  - Tukee hiljaisia tunteja (esim. `22:00`–`07:00`), jolloin yöllä valmistuvan koneen ilmoitus lykätään aamuun.
  - Valinnainen muistutusilmoitus määritetyin väliajoin, kunnes kone kuitataan tyhjennetyksi tai ohjelma vahvistetaan.
- **Virhemerkintöjen korjaus:**
  - Painike viimeisimmän syklin poistamiseen profiilista (`button.<laite>_forget_last`).
  - Palvelut profiilien poistoon (`appliance_monitor.delete_program`) ja historian nollaukseen (`appliance_monitor.clear_history`).
- **Käyttöliittymäkonfigurointi (Config Flow & Options Flow):**
  - Lisäys ja muokkaus suoraan Home Assistantin käyttöliittymästä ilman YAML-määrityksiä.
  - Asetusten muokkaus lennosta nollaamatta käynnissä olevaa sykliä.
  - Täysi monikielituki (suomi ja englanti).

---

## Entiteetit

| Entiteetti | Tyyppi | Kuvaus |
| :--- | :--- | :--- |
| `sensor.<laite>_status` | Sensori (enum) | Laitteen tila (`off`, `idle`, `running`, `paused`, `finished`) |
| `sensor.<laite>_phase` | Sensori (enum) | Syklin vaihe (`idle`, `weighing`, `heating`, `rinsing`, `spinning`, `drying`, `running`) |
| `sensor.<laite>_program` | Sensori | Tunnistettu ohjelma ja arvioitu luotettavuus (`confidence`) |
| `sensor.<laite>_remaining_time` | Sensori (duration) | Arvioitu jäljellä oleva aika (min) |
| `sensor.<laite>_cycle_duration` | Sensori (duration) | Syklin kesto (min) |
| `sensor.<laite>_cycle_energy` | Sensori (energy) | Syklin kulutus (kWh) |
| `binary_sensor.<laite>_running` | Binäärisensori | Käynnissäolotila (`on` kun aktiivinen tai tauolla) |
| `select.<laite>_program_select` | Valitsin (config) | Ohjelman vahvistus ja opetus |
| `text.<laite>_program_text` | Teksti (config) | Uuden ohjelman nimen syöttö ja opetus |
| `button.<laite>_reset` | Painike (config) | Kuittaa valmiustilaan ja lopettaa muistutukset |
| `button.<laite>_forget_last` | Painike (config) | Poistaa edellisen syklin tiedot profiilista |

---

## Palvelut ja tapahtumat

### Palvelut (Services)
- **`appliance_monitor.delete_program`**: Poistaa yksittäisen opitun ohjelmaprofiilin ja sen historianäytteet.
  - Parametrit: `entry_id` (Config Entry ID), `program_name` (poistettavan ohjelman nimi).
- **`appliance_monitor.clear_history`**: Tyhjentää laitteen kaikki opitut ohjelmaprofiilit ja syklihistorian.
  - Parametrit: `entry_id` (Config Entry ID).

### Tapahtumat (Events)
- **`appliance_monitor_started`**: Lähetetään Home Assistantin tapahtumaväylään syklin käynnistyessä (`entry_id`, `name`).
- **`appliance_monitor_finished`**: Lähetetään syklin valmistuessa (`entry_id`, `name`, `duration_minutes`, `energy_kwh`, `predicted_program`).

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

The integration detects cycle phases (heating, spinning, drying, soaking, finished), filters power fluctuations, and estimates the active program and remaining time based on power signature data.

> **Note:** This project is 100% vibe-coded.

---

## Features

- **State Machine and Scheduled Transitions:**
  - Separates soaking pauses from cycle completion using a configurable delay and background timer.
  - Filters out transient power spikes and sensor unavailability (`unavailable` / `unknown`).
  - Restores active cycle state across Home Assistant restarts.
- **Power Signature Engine (EMA Learning):**
  - Identifies programs based on heating phase energy, duration, peak power, and spin stages (including cold washes and heat pump dryers).
  - Adapts over time using an Exponential Moving Average (EMA).
  - Predicts active program and remaining time from learned profiles.
- **Actionable Notifications, Quiet Hours, and Reminders:**
  - Sends a completion notification (duration, kWh) with action buttons to confirm the program.
  - Supports quiet hours (e.g. `22:00`–`07:00`), deferring night-time completion notifications until morning.
  - Optional recurring reminder notifications until the appliance is reset to idle or the program is confirmed.
- **Correction and Profile Management:**
  - Button entity to remove the previous cycle from learned profiles (`button.<appliance>_forget_last`).
  - Services to delete entire program profiles (`appliance_monitor.delete_program`) or clear history (`appliance_monitor.clear_history`).
- **UI Configuration (Config Flow & Options Flow):**
  - Set up and configure via Home Assistant UI without YAML editing.
  - Live options updates without resetting an active cycle.
  - Full localization support for Finnish and English.

---

## Entities

| Entity | Type | Description |
| :--- | :--- | :--- |
| `sensor.<appliance>_status` | Sensor (enum) | Appliance state (`off`, `idle`, `running`, `paused`, `finished`) |
| `sensor.<appliance>_phase` | Sensor (enum) | Cycle phase (`idle`, `weighing`, `heating`, `rinsing`, `spinning`, `drying`, `running`) |
| `sensor.<appliance>_program` | Sensor | Predicted program and confidence (`confidence`) |
| `sensor.<appliance>_remaining_time` | Sensor (duration) | Estimated remaining duration (min) |
| `sensor.<appliance>_cycle_duration` | Sensor (duration) | Cycle duration (min) |
| `sensor.<appliance>_cycle_energy` | Sensor (energy) | Cycle energy consumption (kWh) |
| `binary_sensor.<appliance>_running` | Binary sensor | Activity state (`on` when running or paused) |
| `select.<appliance>_program_select` | Select (config) | Program verification and learning selector |
| `text.<appliance>_program_text` | Text (config) | Custom program name input and learning |
| `button.<appliance>_reset` | Button (config) | Reset state to idle and stop reminders |
| `button.<appliance>_forget_last` | Button (config) | Delete last cycle sample from profile |

---

## Services and Events

### Services
- **`appliance_monitor.delete_program`**: Deletes a learned program profile and removes its sample history.
  - Fields: `entry_id` (Config Entry ID), `program_name` (exact program name).
- **`appliance_monitor.clear_history`**: Wipes all learned program profiles and cycle history for the appliance.
  - Fields: `entry_id` (Config Entry ID).

### Events
- **`appliance_monitor_started`**: Fired on the Home Assistant event bus when a cycle starts (`entry_id`, `name`).
- **`appliance_monitor_finished`**: Fired when a cycle completes (`entry_id`, `name`, `duration_minutes`, `energy_kwh`, `predicted_program`).

---

## Installation

### HACS
1. Open Home Assistant and navigate to **HACS** -> **Integrations**.
2. Select **Custom repositories** from the menu.
3. Add `https://github.com/Valtteri-H/appliance-monitor` with category **Integration**.
4. Download the integration and restart Home Assistant.
5. Go to **Settings** -> **Devices & Services** -> **Add Integration** and search for **Appliance Monitor**.
