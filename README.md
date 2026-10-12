# Appliance Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/Valtteri-H/appliance-monitor)](https://github.com/Valtteri-H/appliance-monitor/releases)

Home Assistant -integraatio kodinkoneiden (pyykinpesukone, astianpesukone, kuivausrumpu) tilan ja syklien valvontaan tehomittausten (W) avulla.

Integraatio tunnistaa ohjelman vaiheet (lämmitys, linkous, liotus, valmis), suodattaa tehonvaihtelut ja arvioi käytetyn ohjelman sekä jäljellä olevan ajan tehodatan pohjalta.

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
  - Käännökset: suomi ja englanti.

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

### Features
- State machine handling wash pauses, soaking intervals, and cycle completions.
- Signature profiling distinguishing heating cycles, spin patterns, and energy metrics.
- Actionable notification support for user program confirmation.
- Built-in correction button and services to manage learned cycle profiles.
- Config Flow and Options Flow UI configuration (English and Finnish).
