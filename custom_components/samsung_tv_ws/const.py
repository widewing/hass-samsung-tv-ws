"""Constants for the Samsung TV WS integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "samsung_tv_ws"

DEFAULT_NAME = "Home Assistant"
DEFAULT_PORT = 8001
DEFAULT_TIMEOUT = 10
UPDATE_INTERVAL = timedelta(seconds=10)
STORAGE_DIR = ".samsung_tv_ws"

CONF_TIMEOUT = "timeout"

PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

ATTR_APP_ID = "app_id"
ATTR_APP_TYPE = "app_type"
ATTR_CATEGORY = "category"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_CONTENT_ID = "content_id"
ATTR_FILE_TYPE = "file_type"
ATTR_KEY = "key"
ATTR_KEY_PRESS_DELAY = "key_press_delay"
ATTR_MATTE = "matte"
ATTR_MATTE_ID = "matte_id"
ATTR_META_TAG = "meta_tag"
ATTR_MODE = "mode"
ATTR_PATH = "path"
ATTR_PORTRAIT_MATTE = "portrait_matte"
ATTR_SHOW = "show"
ATTR_TEXT = "text"
ATTR_TIMES = "times"
ATTR_URL = "url"
ATTR_VALUE = "value"

SERVICE_ART_CHANGE_MATTE = "art_change_matte"
SERVICE_ART_DELETE = "art_delete"
SERVICE_ART_GET_CURRENT = "art_get_current"
SERVICE_ART_GET_MATTE_LIST = "art_get_matte_list"
SERVICE_ART_LIST = "art_list"
SERVICE_ART_SELECT = "art_select"
SERVICE_ART_SET_BRIGHTNESS = "art_set_brightness"
SERVICE_ART_SET_COLOR_TEMPERATURE = "art_set_color_temperature"
SERVICE_ART_SET_MODE = "art_set_mode"
SERVICE_ART_UPLOAD = "art_upload"
SERVICE_GET_DEVICE_INFO = "get_device_info"
SERVICE_LIST_APPS = "list_apps"
SERVICE_OPEN_BROWSER = "open_browser"
SERVICE_RUN_APP = "run_app"
SERVICE_SEND_KEY = "send_key"
SERVICE_SEND_TEXT = "send_text"
