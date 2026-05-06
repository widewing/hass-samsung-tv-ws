"""Service actions for Samsung TV Art."""

from __future__ import annotations

from typing import Any

from samsungtvws import exceptions
import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_APP_ID,
    ATTR_APP_TYPE,
    ATTR_CATEGORY,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_CONTENT_ID,
    ATTR_FILE_TYPE,
    ATTR_KEY,
    ATTR_KEY_PRESS_DELAY,
    ATTR_MATTE,
    ATTR_MATTE_ID,
    ATTR_META_TAG,
    ATTR_MODE,
    ATTR_PATH,
    ATTR_PORTRAIT_MATTE,
    ATTR_SHOW,
    ATTR_TEXT,
    ATTR_TIMES,
    ATTR_URL,
    ATTR_VALUE,
    DOMAIN,
    SERVICE_ART_CHANGE_MATTE,
    SERVICE_ART_DELETE,
    SERVICE_ART_GET_CURRENT,
    SERVICE_ART_GET_MATTE_LIST,
    SERVICE_ART_LIST,
    SERVICE_ART_SELECT,
    SERVICE_ART_SET_BRIGHTNESS,
    SERVICE_ART_SET_COLOR_TEMPERATURE,
    SERVICE_ART_SET_MODE,
    SERVICE_ART_UPLOAD,
    SERVICE_GET_DEVICE_INFO,
    SERVICE_LIST_APPS,
    SERVICE_OPEN_BROWSER,
    SERVICE_RUN_APP,
    SERVICE_SEND_KEY,
    SERVICE_SEND_TEXT,
)
from .coordinator import SamsungTvArtCoordinator


ENTRY_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string})


def async_setup_services(hass: HomeAssistant) -> None:
    """Register Samsung TV Art service actions."""

    async def send_key(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(
            coordinator.async_tv_call(
                "send_key",
                call.data[ATTR_KEY],
                times=call.data[ATTR_TIMES],
                key_press_delay=call.data.get(ATTR_KEY_PRESS_DELAY),
            )
        )

    async def run_app(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(
            coordinator.async_tv_call(
                "run_app",
                call.data[ATTR_APP_ID],
                app_type=call.data[ATTR_APP_TYPE],
                meta_tag=call.data.get(ATTR_META_TAG, ""),
            )
        )

    async def open_browser(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(coordinator.async_tv_call("open_browser", call.data[ATTR_URL]))

    async def send_text(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(coordinator.async_tv_call("send_text", call.data[ATTR_TEXT]))

    async def list_apps(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator_from_call(hass, call)
        apps = await _run(coordinator.async_tv_call("app_list"))
        return {"apps": apps or []}

    async def get_device_info(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator_from_call(hass, call)
        info = await _run(coordinator.async_get_device_info())
        return {"device_info": info}

    async def art_set_mode(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(coordinator.async_art_call("set_artmode", call.data[ATTR_MODE]))

    async def art_get_current(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator_from_call(hass, call)
        current = await _run(coordinator.async_art_call("get_current"))
        return {"current": current}

    async def art_list(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator_from_call(hass, call)
        artworks = await _run(
            coordinator.async_art_call("available", call.data.get(ATTR_CATEGORY))
        )
        return {"artworks": artworks or []}

    async def art_get_matte_list(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator_from_call(hass, call)
        mattes = await _run(coordinator.async_art_call("get_matte_list"))
        return {"mattes": mattes or {}}

    async def art_upload(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _coordinator_from_call(hass, call)
        content_id = await _run(
            coordinator.async_art_call(
                "upload",
                call.data[ATTR_PATH],
                matte=call.data[ATTR_MATTE],
                portrait_matte=call.data[ATTR_PORTRAIT_MATTE],
                file_type=call.data[ATTR_FILE_TYPE],
            )
        )
        if getattr(call, "return_response", False):
            return {"content_id": content_id}
        return None

    async def art_select(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(
            coordinator.async_art_call(
                "select_image",
                call.data[ATTR_CONTENT_ID],
                category=call.data.get(ATTR_CATEGORY),
                show=call.data[ATTR_SHOW],
            )
        )

    async def art_delete(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(coordinator.async_art_call("delete", call.data[ATTR_CONTENT_ID]))

    async def art_change_matte(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(
            coordinator.async_art_call(
                "change_matte",
                call.data[ATTR_CONTENT_ID],
                matte_id=call.data[ATTR_MATTE_ID],
                portrait_matte=call.data.get(ATTR_PORTRAIT_MATTE),
            )
        )

    async def art_set_brightness(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(coordinator.async_art_call("set_brightness", call.data[ATTR_VALUE]))

    async def art_set_color_temperature(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await _run(
            coordinator.async_art_call("set_color_temperature", call.data[ATTR_VALUE])
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_KEY,
        send_key,
        schema=ENTRY_SCHEMA.extend(
            {
                vol.Required(ATTR_KEY): cv.string,
                vol.Optional(ATTR_TIMES, default=1): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=20)
                ),
                vol.Optional(ATTR_KEY_PRESS_DELAY): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=10)
                ),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_APP,
        run_app,
        schema=ENTRY_SCHEMA.extend(
            {
                vol.Required(ATTR_APP_ID): cv.string,
                vol.Optional(ATTR_APP_TYPE, default="DEEP_LINK"): vol.In(
                    ["DEEP_LINK", "NATIVE_LAUNCH"]
                ),
                vol.Optional(ATTR_META_TAG, default=""): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_BROWSER,
        open_browser,
        schema=ENTRY_SCHEMA.extend({vol.Required(ATTR_URL): cv.url}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TEXT,
        send_text,
        schema=ENTRY_SCHEMA.extend({vol.Required(ATTR_TEXT): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_APPS,
        list_apps,
        schema=ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DEVICE_INFO,
        get_device_info,
        schema=ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_SET_MODE,
        art_set_mode,
        schema=ENTRY_SCHEMA.extend({vol.Required(ATTR_MODE): cv.boolean}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_GET_CURRENT,
        art_get_current,
        schema=ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_LIST,
        art_list,
        schema=ENTRY_SCHEMA.extend({vol.Optional(ATTR_CATEGORY): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_GET_MATTE_LIST,
        art_get_matte_list,
        schema=ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_UPLOAD,
        art_upload,
        schema=ENTRY_SCHEMA.extend(
            {
                vol.Required(ATTR_PATH): cv.string,
                vol.Optional(ATTR_MATTE, default="shadowbox_polar"): cv.string,
                vol.Optional(ATTR_PORTRAIT_MATTE, default="shadowbox_polar"): cv.string,
                vol.Optional(ATTR_FILE_TYPE, default="png"): vol.In(
                    ["jpg", "jpeg", "png"]
                ),
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_SELECT,
        art_select,
        schema=ENTRY_SCHEMA.extend(
            {
                vol.Required(ATTR_CONTENT_ID): cv.string,
                vol.Optional(ATTR_CATEGORY): cv.string,
                vol.Optional(ATTR_SHOW, default=True): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_DELETE,
        art_delete,
        schema=ENTRY_SCHEMA.extend({vol.Required(ATTR_CONTENT_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_CHANGE_MATTE,
        art_change_matte,
        schema=ENTRY_SCHEMA.extend(
            {
                vol.Required(ATTR_CONTENT_ID): cv.string,
                vol.Required(ATTR_MATTE_ID): cv.string,
                vol.Optional(ATTR_PORTRAIT_MATTE): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_SET_BRIGHTNESS,
        art_set_brightness,
        schema=ENTRY_SCHEMA.extend({vol.Required(ATTR_VALUE): vol.Coerce(int)}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ART_SET_COLOR_TEMPERATURE,
        art_set_color_temperature,
        schema=ENTRY_SCHEMA.extend({vol.Required(ATTR_VALUE): vol.Coerce(int)}),
    )


async def _run(awaitable: Any) -> Any:
    """Run a service awaitable and convert library failures to HA errors."""
    try:
        return await awaitable
    except (
        exceptions.ConnectionFailure,
        exceptions.HttpApiError,
        exceptions.ResponseError,
        exceptions.UnauthorizedError,
        TimeoutError,
        OSError,
        ValueError,
    ) as err:
        raise HomeAssistantError(f"Samsung TV Art service failed: {err}") from err


def _coordinator_from_call(
    hass: HomeAssistant,
    call: ServiceCall,
) -> SamsungTvArtCoordinator:
    """Resolve a service call to a loaded config entry coordinator."""
    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator is None:
        raise HomeAssistantError(
            f"Samsung TV Art config entry is not loaded: {entry_id}"
        )
    return coordinator
