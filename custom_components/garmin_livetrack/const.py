DOMAIN = "garmin_livetrack"

GARMIN_API_URL = "https://livetrack.garmin.com/services/session/{session_id}/trackpoints"
GARMIN_API_HEADERS = {"NK": "NT", "Accept": "application/json"}

CONF_NOTIFY_SERVICE = "notify_service"
CONF_POLL_INTERVAL = "poll_interval"
CONF_TRACKER_NAME = "tracker_name"

DEFAULT_POLL_INTERVAL = 60
DEFAULT_TRACKER_NAME = "Garmin"
SESSION_TIMEOUT_HOURS = 24
