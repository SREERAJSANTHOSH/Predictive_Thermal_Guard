"""Optional MQTT telemetry adapter."""

import asyncio
import json
import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode
from pydantic import ValidationError

from .config import Settings
from .models import DeviceTelemetry, Transport
from .service import ThermalGuardService

LOGGER = logging.getLogger(__name__)


class MqttAdapter:
    def __init__(
        self,
        settings: Settings,
        service: ThermalGuardService,
        loop: asyncio.AbstractEventLoop,
        client_factory: Callable[[], mqtt.Client] | None = None,
    ) -> None:
        self.settings = settings
        self.service = service
        self.loop = loop
        factory = client_factory or (
            lambda: mqtt.Client(CallbackAPIVersion.VERSION2, client_id="thermal-guard-api")
        )
        self.client = factory()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    def start(self) -> None:
        self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, 60)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        del userdata, flags, properties
        if reason_code == 0:
            client.subscribe(self.settings.mqtt_topic, qos=1)
            LOGGER.info("subscribed to %s", self.settings.mqtt_topic)
        else:
            LOGGER.error("MQTT connection failed: %s", reason_code)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        del client, userdata
        try:
            telemetry = DeviceTelemetry.model_validate_json(message.payload)
            for reading in telemetry.readings:
                reading.transport = Transport.MQTT
        except (ValidationError, json.JSONDecodeError) as error:
            LOGGER.warning("rejected MQTT payload on %s: %s", message.topic, error)
            return
        asyncio.run_coroutine_threadsafe(
            self.service.ingest_telemetry(telemetry),
            self.loop,
        )
