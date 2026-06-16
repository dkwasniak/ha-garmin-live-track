DOMAIN = "garmin_livetrack"
INTEGRATION_VERSION = "1.0.2"

GARMIN_API_URL = "https://livetrack.garmin.com/api/sessions/{session_id}/track-points/common"
GARMIN_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:151.0) "
    "Gecko/20100101 Firefox/151.0"
)
GARMIN_API_HEADERS = {"Accept": "application/json", "User-Agent": GARMIN_USER_AGENT}
GARMIN_PAGE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": GARMIN_USER_AGENT,
}

CONF_NOTIFY_SERVICE = "notify_service"
CONF_POLL_INTERVAL = "poll_interval"
CONF_TRACKER_NAME = "tracker_name"

DEFAULT_POLL_INTERVAL = 60
DEFAULT_TRACKER_NAME = "Garmin"
SESSION_TIMEOUT_HOURS = 24
