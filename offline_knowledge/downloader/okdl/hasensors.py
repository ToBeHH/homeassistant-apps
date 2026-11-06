"""Sensors in Home Assistant through MQTT discovery.

MQTT and not the Core API: homeassistant_api would give this container full
access to Home Assistant, next to a library port without a login. A broker
login is all this needs, and the entities get unique IDs and a device page.

Each update is a short connection of its own, so nothing has to be kept alive.
expire_after marks the sensors unavailable when the app stops sending. Without
a broker nothing happens, and one that is added later is picked up.
"""

import json
import logging
import os
import shutil
import socket
import ssl
import struct
import threading
import time
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

SUPERVISOR = "http://supervisor"
DISCOVERY = "homeassistant/sensor/offline_knowledge/{key}/config"
STATE_TOPIC = "offline_knowledge/state"
CLIENT_ID = "offline_knowledge"
POLL = 60
REFRESH = 300
EXPIRE_AFTER = 900
TIMEOUT = 15
CONTENT_DIRS = ("zim", "maps", "geocode")
PROBLEM_STATES = ("error", "no_space", "no_memory")
GB = 1000**3

SENSORS = {
    "status": {"name": "Status", "icon": "mdi:bookshelf"},
    "free_space": {
        "name": "Free space",
        "device_class": "data_size",
        "state_class": "measurement",
        "unit_of_measurement": "GB",
        "suggested_display_precision": 1,
    },
    "content_size": {
        "name": "Content size",
        "device_class": "data_size",
        "state_class": "measurement",
        "unit_of_measurement": "GB",
        "suggested_display_precision": 1,
        "icon": "mdi:database",
    },
    "last_update": {"name": "Last update", "device_class": "timestamp"},
}


class MqttError(Exception):
    pass


def discovery(slug, version):
    """Topic -> payload of the entity configurations."""
    device = {
        "identifiers": ["offline_knowledge"],
        "name": "Offline Knowledge",
        "model": "Home Assistant app",
        "sw_version": version,
        "configuration_url": f"homeassistant://app/{slug}",
    }
    out = {}
    for key, sensor in SENSORS.items():
        config = {
            "unique_id": f"offline_knowledge_{key}",
            "has_entity_name": True,
            "state_topic": STATE_TOPIC,
            # null ends up as "None", which Home Assistant shows as unknown.
            "value_template": f"{{{{ value_json.{key} }}}}",
            "expire_after": EXPIRE_AFTER,
            "device": device,
            **sensor,
        }
        if key == "status":
            config["json_attributes_topic"] = STATE_TOPIC
            config["json_attributes_template"] = "{{ value_json.details | tojson }}"
        out[DISCOVERY.format(key=key)] = json.dumps(config)
    return out


def content_bytes(data_path):
    total = 0
    for name in CONTENT_DIRS:
        try:
            with os.scandir(os.path.join(data_path, name)) as files:
                for f in files:
                    if f.is_file() and not f.name.endswith(".part"):
                        total += f.stat().st_size
        except OSError:
            continue
    return total


def _gb(n):
    return round(n / GB, 1)


def read_state(status_path, data_path):
    """What the sensors show. Read from the status file: the downloader writes it
    atomically, so this thread never sees half a change."""
    try:
        with open(status_path, encoding="utf-8") as f:
            status = json.load(f)
    except (OSError, ValueError):
        status = {}
    free = content = None
    if data_path and os.path.isdir(data_path):
        free = _gb(shutil.disk_usage(data_path).free)
        content = _gb(content_bytes(data_path))
    items = status.get("items", {})
    return {
        "status": status.get("state", "starting"),
        "free_space": free,
        "content_size": content,
        "last_update": status.get("last_success"),
        "details": {
            "message": status.get("message"),
            "problems": sorted(
                i.get("title") or key
                for key, i in items.items()
                if i.get("state") in PROBLEM_STATES
            ),
            "last_check": status.get("last_check"),
            "next_check": status.get("next_check"),
        },
    }


# --- MQTT 3.1.1, just enough to publish -----------------------------------------


def _text(value):
    data = value.encode("utf-8")
    return struct.pack("!H", len(data)) + data


def _packet(first, body):
    length = len(body)
    encoded = bytearray()
    while True:
        length, digit = length // 128, length % 128
        encoded.append(digit | (0x80 if length else 0))
        if not length:
            break
    return bytes([first]) + bytes(encoded) + body


def _read(sock, count):
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise MqttError("broker closed the connection")
        data += chunk
    return data


def publish(broker, messages):
    """Send topic -> payload as retained messages; returns once the broker has them."""
    flags = 0x02  # clean session
    body = b"\x00\x04MQTT\x04"
    login = b""
    if broker.get("username"):
        flags |= 0x80
        login += _text(broker["username"])
    if broker.get("password"):
        flags |= 0x40
        login += _text(broker["password"])
    body += bytes([flags]) + struct.pack("!H", TIMEOUT * 4) + _text(CLIENT_ID) + login

    with socket.create_connection((broker["host"], int(broker["port"])), TIMEOUT) as raw:
        sock = raw
        if broker.get("ssl"):
            # The broker's certificate is usually its own; the link is inside the host.
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(raw)
        sock.settimeout(TIMEOUT)
        sock.sendall(_packet(0x10, body))
        ack = _read(sock, 4)
        if ack[0] != 0x20 or ack[3] != 0:
            raise MqttError(f"broker refused the connection (code {ack[3]})")
        for number, (topic, payload) in enumerate(messages.items(), start=1):
            # QoS 1, retained: Home Assistant finds them after its own restart.
            sock.sendall(_packet(0x33, _text(topic) + struct.pack("!H", number) + payload.encode("utf-8")))
            ack = _read(sock, 4)
            if ack[0] != 0x40 or struct.unpack("!H", ack[2:])[0] != number:
                raise MqttError("broker did not confirm a message")
        sock.sendall(_packet(0xE0, b""))


# --- Supervisor ------------------------------------------------------------------


def _supervisor(path, token, base):
    request = urllib.request.Request(base + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as r:
        return json.load(r)["data"]


def broker_settings(token, base=SUPERVISOR):
    """The broker's address and login, or None if there is no broker."""
    try:
        return _supervisor("/services/mqtt", token, base)
    except urllib.error.HTTPError as err:
        err.close()
        if err.code in (400, 404):
            return None
        raise


class Publisher:
    def __init__(self, status_path, data_path, token, supervisor=SUPERVISOR):
        self.status_path = status_path
        self.data_path = data_path
        self.token = token
        self.supervisor = supervisor
        self.app = None
        self.sent = None
        self.refreshed_at = 0
        self.problem = None  # logged once per kind of trouble

    def _note(self, problem, level=logging.WARNING):
        if problem != self.problem:
            self.problem = problem
            log.log(level, "Home Assistant sensors: %s", problem)

    def tick(self, now=None):
        """One round; sends if something changed or it is time to refresh."""
        now = time.monotonic() if now is None else now
        state = read_state(self.status_path, self.data_path)
        refresh = self.sent is None or now - self.refreshed_at >= REFRESH
        if state == self.sent and not refresh:
            return
        try:
            broker = broker_settings(self.token, self.supervisor)
            if broker is None:
                self._note("no MQTT broker found, nothing is sent", logging.INFO)
                return
            if self.app is None:
                self.app = _supervisor("/addons/self/info", self.token, self.supervisor)
            messages = {}
            if refresh:
                # Each time: a broker without persistence forgets them on a restart.
                messages.update(discovery(self.app["slug"], self.app.get("version", "")))
            messages[STATE_TOPIC] = json.dumps(state)
            publish(broker, messages)
        except (OSError, ValueError, KeyError, MqttError) as err:
            self._note(f"can't send ({err}), trying again")
            return
        self.sent = state
        if refresh:
            self.refreshed_at = now
        self._note("sending to the MQTT broker", logging.INFO)

    def run(self):
        while True:
            try:
                self.tick()
            except Exception:  # never take the downloader down with it
                log.exception("Home Assistant sensors failed")
            time.sleep(POLL)


def start(status_path, data_path):
    """In the background; does nothing outside the Supervisor."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None
    publisher = Publisher(status_path, data_path, token)
    threading.Thread(target=publisher.run, name="hasensors", daemon=True).start()
    return publisher
