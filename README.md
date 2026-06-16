# Garmin LiveTrack for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration that receives
[Garmin LiveTrack](https://support.garmin.com/en-US/?faq=tEIuGMFRCH5v9BTZWO6JNA)
session notifications via a [Cloudflare Email Worker](https://developers.cloudflare.com/email-routing/email-workers/)
and tracks the athlete's GPS position, speed, altitude, and heart rate in real time.

## How it works

```
Garmin watch → starts activity with LiveTrack
      ↓
Garmin sends email to your @yourdomain.com address
      ↓
Cloudflare Email Worker parses the LiveTrack URL
      ↓
Worker calls Home Assistant webhook
      ↓
Integration polls Garmin LiveTrack API every 60 s
      ↓
Position and telemetry appear in HA entities
```

## Features

- **Live location** — `device_tracker` entity shown on the HA map with history.
- **Telemetry sensors** — speed, heart rate, altitude, and session URL.
- **Push notification** — optional notification on your phone when a session starts.
- **Stop button** — manually end tracking from HA UI.
- **Auto-expire** — session automatically stops after 24 hours.
- **UI configuration** — no YAML required.

## Entities

| Entity | Type | Notes |
| --- | --- | --- |
| `device_tracker.<name>` | Device tracker | GPS position on the map |
| `sensor.<name>_speed` | Sensor (m/s) | Current speed |
| `sensor.<name>_heart_rate` | Sensor (bpm) | Current heart rate |
| `sensor.<name>_altitude` | Sensor (m) | Current altitude |
| `sensor.<name>_session_url` | Sensor (text) | LiveTrack session URL |
| `sensor.<name>_last_updated` | Sensor (timestamp) | Last position update |
| `button.<name>_stop_tracking` | Button | Manually stop the session |

## Prerequisites

1. A domain managed by **Cloudflare** with Email Routing enabled.
2. A **Cloudflare Email Worker** that receives Garmin emails and calls the HA webhook.
   See [`cloudflare/worker.js`](cloudflare/worker.js) for a ready-to-use worker.
3. Home Assistant reachable from the internet (e.g. via Cloudflare Tunnel).

## Installation

### HACS (recommended)

1. In HACS, open **⋮ → Custom repositories**.
2. Add `https://github.com/dkwasniak/ha-garmin-live-track`, category **Integration**.
3. Find **Garmin LiveTrack** in HACS and click **Download**.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/garmin_livetrack/` to `/config/custom_components/garmin_livetrack/`.
2. Restart Home Assistant.

## Configuration

**Settings → Devices & Services → Add Integration → Garmin LiveTrack**

| Field | Description |
| --- | --- |
| Tracker name | Name for the device tracker and sensor entities. |
| Notification service | Optional, e.g. `notify.mobile_app_pixel_9`. Leave blank to disable. |

After setup, the integration displays the **webhook URL** — copy it into your
Cloudflare Worker as `HA_WEBHOOK_URL`.

Click **Configure** on the integration at any time to adjust:

| Option | Default | Description |
| --- | --- | --- |
| Notification service | — | Service to call when a session starts. |
| Polling interval | 60 s | How often to fetch position from Garmin API. |

## Cloudflare Worker

A ready-to-use worker is included in [`cloudflare/worker.js`](cloudflare/worker.js).
Deploy it to Cloudflare Workers and set the Email Routing rule for your LiveTrack
address to **Send to a Worker**.

## Disclaimer

This project is not affiliated with or endorsed by Garmin. It relies on the
undocumented Garmin LiveTrack API that may change or break at any time.
Use at your own risk.

## License

[MIT](LICENSE)
