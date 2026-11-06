import http.server
import json
import os
import socket
import struct
import tempfile
import threading
import unittest

from okdl import hasensors


class FakeBroker:
    """Speaks the part of MQTT 3.1.1 the publisher needs and notes what arrives."""

    def __init__(self, refuse=0):
        self.refuse = refuse
        self.logins = []
        self.messages = {}
        self.retained = []
        self.sock = socket.create_server(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.done = threading.Event()
        threading.Thread(target=self._serve, daemon=True).start()

    def settings(self):
        return {"host": "127.0.0.1", "port": self.port, "ssl": False,
                "username": "user", "password": "secret"}

    def close(self):
        self.sock.close()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                self._session(conn)
            self.done.set()

    @staticmethod
    def _read(conn, count):
        data = b""
        while len(data) < count:
            chunk = conn.recv(count - len(data))
            if not chunk:
                raise EOFError
            data += chunk
        return data

    def _session(self, conn):
        try:
            while True:
                first = self._read(conn, 1)[0]
                length, shift = 0, 0
                while True:
                    byte = self._read(conn, 1)[0]
                    length |= (byte & 0x7F) << shift
                    shift += 7
                    if not byte & 0x80:
                        break
                body = self._read(conn, length)
                if first == 0x10:
                    self.logins.append(body)
                    conn.sendall(bytes([0x20, 2, 0, self.refuse]))
                    if self.refuse:
                        return
                elif first & 0xF0 == 0x30:
                    size = struct.unpack("!H", body[:2])[0]
                    topic = body[2:2 + size].decode()
                    number = body[2 + size:4 + size]
                    self.messages[topic] = body[4 + size:].decode()
                    self.retained.append(bool(first & 1))
                    conn.sendall(b"\x40\x02" + number)
                elif first == 0xE0:
                    return
        except EOFError:
            return


class FakeSupervisor:
    def __init__(self, broker=None):
        outer = self
        self.broker = broker

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/services/mqtt" and outer.broker:
                    data = outer.broker.settings()
                elif self.path == "/addons/self/info":
                    data = {"slug": "abc_offline_knowledge", "version": "1.2.3"}
                else:
                    self.send_error(400)
                    return
                body = json.dumps({"result": "ok", "data": data}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class DiscoveryTest(unittest.TestCase):
    def test_entities(self):
        out = {t: json.loads(p) for t, p in hasensors.discovery("abc_x", "1.2.3").items()}
        self.assertEqual(len(out), 4)
        free = out["homeassistant/sensor/offline_knowledge/free_space/config"]
        self.assertEqual(free["unique_id"], "offline_knowledge_free_space")
        self.assertEqual(free["unit_of_measurement"], "GB")
        self.assertEqual(free["value_template"], "{{ value_json.free_space }}")
        self.assertEqual(free["device"]["configuration_url"], "homeassistant://app/abc_x")
        self.assertEqual(free["device"]["sw_version"], "1.2.3")
        self.assertIn("json_attributes_topic", out["homeassistant/sensor/offline_knowledge/status/config"])
        self.assertNotIn("json_attributes_topic", free)


class ReadStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.status = os.path.join(self.tmp.name, "status.json")
        self.data = os.path.join(self.tmp.name, "data")

    def write(self, rel, size):
        path = os.path.join(self.data, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.truncate(size)

    def test_before_anything_exists(self):
        state = hasensors.read_state(self.status, "")
        self.assertEqual(state["status"], "starting")
        self.assertIsNone(state["free_space"])
        self.assertIsNone(state["content_size"])
        self.assertIsNone(state["last_update"])

    def test_counts_finished_content_only(self):
        self.write("zim/a.zim", 2_000_000_000)
        self.write("zim/b.zim.part", 9_000_000_000)
        self.write("maps/w.pmtiles", 500_000_000)
        self.write("maps/x.pmtiles.part", 9_000_000_000)
        self.write("geocode/g.sqlite", 100_000_000)
        self.write("other/not-content", 9_000_000_000)
        state = hasensors.read_state(self.status, self.data)
        self.assertEqual(state["content_size"], 2.6)
        self.assertGreater(state["free_space"], 0)

    def test_status_and_problems(self):
        with open(self.status, "w", encoding="utf-8") as f:
            json.dump({
                "state": "idle",
                "message": "finished with problems",
                "last_success": "2026-11-06T09:50:01+00:00",
                "next_check": "2026-11-13T09:50:01+00:00",
                "items": {
                    "map:asia": {"state": "no_memory", "title": "Asia"},
                    "x": {"state": "error"},
                    "y": {"state": "current", "title": "Fine"},
                },
            }, f)
        state = hasensors.read_state(self.status, "")
        self.assertEqual(state["status"], "idle")
        self.assertEqual(state["last_update"], "2026-11-06T09:50:01+00:00")
        self.assertEqual(state["details"]["problems"], ["Asia", "x"])
        self.assertEqual(state["details"]["next_check"], "2026-11-13T09:50:01+00:00")


class PublishTest(unittest.TestCase):
    def test_long_payload_and_login(self):
        broker = FakeBroker()
        self.addCleanup(broker.close)
        payload = "x" * 70000  # takes three bytes of length
        hasensors.publish(broker.settings(), {"a/b": payload, "c": "1"})
        self.assertEqual(broker.messages, {"a/b": payload, "c": "1"})
        self.assertEqual(broker.retained, [True, True])
        self.assertIn(b"user", broker.logins[0])
        self.assertIn(b"secret", broker.logins[0])

    def test_refused(self):
        broker = FakeBroker(refuse=5)
        self.addCleanup(broker.close)
        with self.assertRaises(hasensors.MqttError):
            hasensors.publish(broker.settings(), {"a": "1"})
        self.assertEqual(broker.messages, {})


class PublisherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.status = os.path.join(self.tmp.name, "status.json")
        self.set_state("idle")

    def set_state(self, state):
        with open(self.status, "w", encoding="utf-8") as f:
            json.dump({"state": state, "items": {}}, f)

    def publisher(self, sup):
        return hasensors.Publisher(self.status, self.tmp.name, "tok", supervisor=sup.url)

    def setup_broker(self):
        broker = FakeBroker()
        self.addCleanup(broker.close)
        sup = FakeSupervisor(broker)
        self.addCleanup(sup.close)
        return broker, sup

    def test_sends_config_and_state(self):
        broker, sup = self.setup_broker()
        self.publisher(sup).tick(now=1000)
        self.assertEqual(len(broker.messages), 5)
        self.assertEqual(json.loads(broker.messages[hasensors.STATE_TOPIC])["status"], "idle")
        config = json.loads(broker.messages["homeassistant/sensor/offline_knowledge/status/config"])
        self.assertEqual(config["device"]["configuration_url"],
                         "homeassistant://app/abc_offline_knowledge")

    def test_only_when_changed_or_due(self):
        broker, sup = self.setup_broker()
        p = self.publisher(sup)
        p.tick(now=1000)
        broker.messages.clear()
        p.tick(now=1060)
        self.assertEqual(broker.messages, {})
        self.set_state("downloading")
        p.tick(now=1120)
        self.assertEqual(list(broker.messages), [hasensors.STATE_TOPIC])
        broker.messages.clear()
        p.tick(now=1000 + hasensors.REFRESH + 1)
        self.assertEqual(len(broker.messages), 5)

    def test_no_broker_then_one_appears(self):
        sup = FakeSupervisor()
        self.addCleanup(sup.close)
        p = self.publisher(sup)
        p.tick(now=1000)
        self.assertIsNone(p.sent)
        broker = FakeBroker()
        self.addCleanup(broker.close)
        sup.broker = broker
        p.tick(now=1060)
        self.assertEqual(len(broker.messages), 5)

    def test_broker_down_is_retried(self):
        broker, sup = self.setup_broker()
        working = broker.settings()
        down = dict(working, port=1)

        class Dead:
            @staticmethod
            def settings():
                return down

        sup.broker = Dead
        p = self.publisher(sup)
        with self.assertLogs("okdl.hasensors", level="WARNING"):
            p.tick(now=1000)
        self.assertIsNone(p.sent)
        sup.broker = broker
        p.tick(now=1060)
        self.assertEqual(len(broker.messages), 5)

    def test_password_is_not_logged(self):
        sup = FakeSupervisor()
        self.addCleanup(sup.close)

        class Dead:
            @staticmethod
            def settings():
                return {"host": "127.0.0.1", "port": 1, "username": "user", "password": "secret"}

        sup.broker = Dead
        p = self.publisher(sup)
        with self.assertLogs("okdl.hasensors", level="WARNING") as logs:
            p.tick(now=1000)
        self.assertNotIn("secret", " ".join(logs.output))

    def test_start_needs_a_token(self):
        env = os.environ.pop("SUPERVISOR_TOKEN", None)
        self.addCleanup(lambda: env and os.environ.__setitem__("SUPERVISOR_TOKEN", env))
        self.assertIsNone(hasensors.start(self.status, ""))


if __name__ == "__main__":
    unittest.main()
