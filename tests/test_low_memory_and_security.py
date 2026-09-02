import importlib.util
import os
import pathlib
import sys
import tempfile
import threading
import tracemalloc
import types
import unittest
import urllib.error
import urllib.request
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Block:
    def __init__(self, length):
        self.length = length

    def __len__(self):
        return self.length


class AudioStreamingTests(unittest.TestCase):
    def test_four_hour_merge_has_constant_memory(self):
        sample_rate = 16000
        chunk_frames = sample_rate * 300
        paths = []
        with tempfile.TemporaryDirectory() as temporary:
            for index in range(48):
                path = os.path.join(temporary, f"chunk_{index:03d}.wav")
                pathlib.Path(path).touch()
                paths.append(path)

            class Source:
                samplerate = sample_rate
                channels = 1

                def __init__(self):
                    self.remaining = chunk_frames

                def __enter__(self): return self
                def __exit__(self, *args): return False

                def read(self, count, **kwargs):
                    size = min(count, self.remaining)
                    self.remaining -= size
                    return Block(size)

            class Destination:
                written = 0
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def write(self, block): self.written += len(block)

            destination = Destination()

            def sound_file(path, mode="r", **kwargs):
                return destination if mode == "w" else Source()

            soundfile = types.SimpleNamespace(SoundFile=sound_file)

            class Result:
                def fetchall(self): return [{"file_path": path} for path in paths]

            class Connection:
                def execute(self, *args): return Result()
                def commit(self): pass
                def close(self): pass

            config = types.SimpleNamespace(SAMPLE_RATE=sample_rate, DATA_DIR=temporary)
            database = types.SimpleNamespace(get_connection=lambda: Connection())
            with mock.patch.dict(sys.modules, {"soundfile": soundfile, "config": config, "database": database}):
                module = load_module(
                    "audio_chunker_under_test", ROOT / "agent_windows" / "audio_chunker.py"
                )
                session_folder = os.path.join(temporary, "sessions", "test")
                tracemalloc.start()
                module.merge_chunks(1, session_folder)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

            self.assertEqual(destination.written, sample_rate * 4 * 60 * 60)
            self.assertLess(peak, 4 * 1024 * 1024)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        config = types.SimpleNamespace(
            DATA_DIR=self.temporary.name,
            DB_PATH=os.path.join(self.temporary.name, "test.db"),
            MAX_RETRY=3,
        )
        with mock.patch.dict(sys.modules, {"config": config}):
            self.db = load_module(
                "worker_database_under_test", ROOT / "pipeline_worker" / "database.py"
            )
        self.db.init_db()

    def tearDown(self):
        self.temporary.cleanup()

    def _insert_job(self, status="pending", age_days=0):
        folder = os.path.join(self.temporary.name, "sessions", "meeting")
        os.makedirs(os.path.join(folder, "outputs"), exist_ok=True)
        connection = self.db.get_connection()
        cursor = connection.execute(
            "INSERT INTO sessions(title, status, folder_path, stopped_at) "
            "VALUES('test', 'archived', 'sessions/meeting', datetime('now', ?))",
            (f"-{age_days} days",),
        )
        session_id = cursor.lastrowid
        cursor = connection.execute(
            "INSERT INTO jobs(session_id, job_type, status) VALUES(?, 'full_pipeline', ?)",
            (session_id, status),
        )
        connection.commit()
        connection.close()
        return session_id, cursor.lastrowid

    def test_claim_is_atomic(self):
        _, job_id = self._insert_job()
        self.assertEqual(self.db.claim_next_pending_job()["id"], job_id)
        self.assertIsNone(self.db.claim_next_pending_job())

    def test_running_job_is_requeued_after_restart(self):
        _, job_id = self._insert_job("running")
        recovered, failed = self.db.recover_stuck_jobs()
        self.assertEqual((recovered, failed), (1, 0))
        job = self.db.claim_next_pending_job()
        self.assertEqual(job["id"], job_id)
        self.assertEqual(job["retry_count"], 1)

    def test_retention_purges_documents_after_seven_days(self):
        session_id, _ = self._insert_job(age_days=8)
        self.assertEqual(self.db.purge_expired_sessions(7), 1)
        self.assertIsNone(self.db.get_session(session_id))


class SecurityTests(unittest.TestCase):
    def test_proxy_rejects_unauthenticated_network_request(self):
        config = types.SimpleNamespace(
            OLLAMA_PROXY_BIND="127.0.0.1", OLLAMA_PROXY_PORT=0,
            OLLAMA_PROXY_TOKEN="s" * 64, OLLAMA_UPSTREAM_URL="http://127.0.0.1:11434",
        )
        requests = types.ModuleType("requests")
        requests.RequestException = RuntimeError
        with mock.patch.dict(sys.modules, {"config": config, "requests": requests}):
            module = load_module("proxy_under_test", ROOT / "agent_windows" / "ollama_proxy.py")
        server = module.ThreadingHTTPServer(("127.0.0.1", 0), module._ProxyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/version"
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(url, timeout=2)
            self.assertEqual(raised.exception.code, 401)
        finally:
            server.shutdown()
            server.server_close()

    def test_usb_copy_uses_sha256(self):
        config = types.SimpleNamespace(
            SESSIONS_DIR="", USB_REQUIRE_BITLOCKER=True, USB_SECRET="secret",
            USB_SECRET_FILE=".token", USB_TARGET_LABEL="RESUMER", USB_VOLUME_SERIAL="ABC",
        )
        notifier = types.SimpleNamespace(
            bip_error=lambda: None, bip_usb_detected=lambda: None, bip_usb_done=lambda: None
        )
        with mock.patch.dict(sys.modules, {"config": config, "notifier": notifier}):
            module = load_module("usb_under_test", ROOT / "agent_windows" / "usb_listener.py")
        with tempfile.TemporaryDirectory() as temporary:
            source = os.path.join(temporary, "source.docx")
            destination = os.path.join(temporary, "destination.docx")
            pathlib.Path(source).write_bytes(b"document")
            self.assertEqual(module._verified_copy(source, destination), "copie_verifiee")
            self.assertEqual(module._sha256(source), module._sha256(destination))

    def test_ollama_requests_are_authenticated_and_bounded(self):
        config = types.SimpleNamespace(
            OLLAMA_FALLBACK_MODEL="qwen3.5:0.8b",
            OLLAMA_MODEL="granite4.1:3b",
            OLLAMA_PROXY_TOKEN="x" * 64,
            OLLAMA_URL="http://proxy:11435",
        )
        requests = types.ModuleType("requests")
        requests.RequestException = RuntimeError
        requests.post = mock.Mock()
        with mock.patch.dict(sys.modules, {"config": config, "requests": requests}):
            module = load_module("ollama_under_test", ROOT / "pipeline_worker" / "ollama_client.py")
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"response": "resume"}
        with mock.patch.object(module.requests, "post", return_value=response) as post:
            result = module.generate_text("transcription", 0.1, 2048, 8192, 30)
        self.assertEqual(result, "resume")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer " + "x" * 64)
        self.assertEqual(kwargs["json"]["options"]["num_ctx"], 8192)
        self.assertEqual(kwargs["json"]["options"]["num_predict"], 2048)

    def test_windows_path_maps_to_container_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = types.SimpleNamespace(DATA_DIR=temporary, DIARIZATION_ENABLED=False)
            with mock.patch.dict(
                sys.modules,
                {
                    "config": config,
                    "database": types.SimpleNamespace(),
                    "ollama_client": types.SimpleNamespace(unload_model=lambda: None),
                },
            ):
                module = load_module(
                    "pipeline_under_test", ROOT / "pipeline_worker" / "pipeline.py"
                )
            result = module._resolve_session_folder_for_worker(
                r"C:\poste\stt_app\data\sessions\Reunion_001"
            )
            expected = os.path.realpath(os.path.join(temporary, "sessions", "Reunion_001"))
            self.assertEqual(result, expected)

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = types.SimpleNamespace(DATA_DIR=temporary, DIARIZATION_ENABLED=False)
            with mock.patch.dict(
                sys.modules,
                {
                    "config": config,
                    "database": types.SimpleNamespace(),
                    "ollama_client": types.SimpleNamespace(unload_model=lambda: None),
                },
            ):
                module = load_module(
                    "pipeline_traversal_test", ROOT / "pipeline_worker" / "pipeline.py"
                )
            with self.assertRaises(ValueError):
                module._resolve_session_folder_for_worker("sessions/../../outside")


if __name__ == "__main__":
    unittest.main()
