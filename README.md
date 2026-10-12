# Appliance Monitor (Laitevahti) for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/Valtteri-H/appliance-monitor)](https://github.com/Valtteri-H/appliance-monitor/releases)

Älykäs ja adaptiivinen Home Assistant -integraatio, joka tarkkailee kodinkoneiden (pyykinpesukone, astianpesukone, kuivausrumpu) toimintaa älypistorasioiden tehonmittauksen (W) perusteella.

Integraatio tunnistaa syklin vaiheet luotettavasti suodattaen liotus- ja taukovaiheet, kerää pesuohjelmien tehoprofiilit ja oppii ennustamaan käytetyn ohjelman sekä jäljellä olevan pesuajan.

---

## Keskeiset ominaisuudet

- **Luotettava tilakone (Failsafe State Machine):**
  - Erottaa liotus- ja lämmitystauot syklin päättymisestä säädettävällä viiveellä.
  - Suodattaa satunnaiset tehoheilahdukset ja virtapiikit.
- **Oppiva ohjelmantunnistus (Power Signature Engine):**
  - Tunnistaa lämmitysvaiheen energian ja keston perusteella tavoitelämpötilat (30 °C, 40 °C, 60 °C, 90 °C).
  - Havaitsee linkousvaiheet ja punnituspyöritykset.
  - Ennustaa käynnissä olevan ohjelman ja arvioidun valmistumisajan (ETA).
- **Interaktiiviset mobiili-ilmoitukset (Actionable Notifications):**
  - Lähettää puhelimeen ilmoituksen pesun valmistuttua keston ja kulutuksen kera.
  - Pikanapit ohjelman vahvistamiseen suoraan ilmoituksesta.
- **Virhemerkintöjen poisto ja hallinta:**
  - Painike viimeisimmän opitun syklin unohtamiseen (`button.<laite>_forget_last_cycle`).
  - Home Assistant -palvelut: `appliance_monitor.delete_program` ja `appliance_monitor.clear_history`.
- **Yleiskäyttöinen asennus suoraan käyttöliittymästä (Config Flow):**
  - Lisää useita koneita (pyykkikone, tiskikone, kuivausrumpu) ilman YAML-konfiguraatiota.
  - Toimii minkä tahansa Zigbee-, Shelly-, Tuya- tai Z-Wave-tehosensorin kanssa.
  - Täysi tuki suomeksi ja englanniksi.

---

## Luotavat entiteetit

| Entiteetti | Tyyppi | Kuvaus |
| :--- | :--- | :--- |
| `sensor.<laite>_status` | Sensori | Laitteen tila (`idle`, `running`, `paused`, `finished`) |
| `sensor.<laite>_phase` | Sensori | Syklin vaihe (`weighing`, `heating`, `rinsing`, `spinning`) |
| `sensor.<laite>_program` | Sensori | Tunnistettu ohjelma ja varmuusprosentti |
| `sensor.<laite>_remaining_time` | Sensori | Arvioitu jäljellä oleva aika (minuuttia) |
| `sensor.<laite>_cycle_duration` | Sensori | Syklin kesto (minuuttia) |
| `sensor.<laite>_cycle_energy` | Sensori | Syklin sähkönkulutus (kWh) |
| `binary_sensor.<laite>_running` | Binäärisensori | Päällä (`on` kun käynnissä tai tauolla) |
| `select.<laite>_program_select` | Valitsin | Viimeisimmän syklin ohjelman vahvistus tai opetus |
| `button.<laite>_reset` | Painike | Kuittaa laitteen takaisin valmiustilaan |
| `button.<laite>_forget_last` | Painike | Poistaa viimeisimmän syklin datan profiilista |

---

## Asennus

### HACS (Suositeltu tapa)
1. Avaa Home Assistantissa **HACS** -> **Integrations**.
2. Valitse oikeasta yläkulmasta kolme pistettä -> **Custom repositories**.
3. Lisää osoite: `https://github.com/Valtteri-H/appliance-monitor` ja tyypiksi **Integration**.
4. Klikkaa **Download** ja käynnistä Home Assistant uudelleen.
5. Siirry valikkoon **Asetukset** -> **Laitteet ja palvelut** -> **Lisää integraatio** ja etsi **Appliance Monitor**.

---

# English Documentation 🇬🇧

Appliance Monitor is an intelligent and adaptive Home Assistant custom component that tracks washing machines, dishwashers, and dryers using smart plug power measurements (W).

### Features
- **Failsafe State Machine:** Distinguishes soaking pauses from cycle completion without false alarms.
- **Adaptive Signature Learning:** Analyzes heating durations, spin profiles, and energy consumption to identify wash programs and predict remaining cycle time.
- **Actionable Notifications:** Prompts your mobile device upon cycle completion with quick-action buttons to label or verify the program.
- **Correction Support:** Built-in entity button and services to undo or delete misclassified learning samples.
- **Full UI Configuration:** Complete Config Flow and Options Flow with multi-language support (English and Finnish).
