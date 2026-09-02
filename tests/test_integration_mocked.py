import json
import os
import pathlib
import sys
import tempfile
import types
import unittest
import wave
from unittest import mock

from test_low_memory_and_security import ROOT, load_module


class SimulatedPipelineIntegrationTest(unittest.TestCase):
    """Traverse le pipeline avec audio PCM synthetique et service Ollama simule."""

    def test_synthetic_audio_to_draft_documents(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = pathlib.Path(temporary) / "sessions" / "Reunion_test"
            audio_dir = session / "audio"
            audio_dir.mkdir(parents=True)
            audio_path = audio_dir / "final.wav"
            with wave.open(str(audio_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\x00\x00" * 16000)

            config = types.SimpleNamespace(
                DATA_DIR=temporary,
                DIARIZATION_ENABLED=False,
                GLOBAL_CTX=8192,
                PV_PREDICT=2048,
                PV_TEMPERATURE=0.1,
                PV_TIMEOUT=30,
                SUMMARY_PREDICT=2048,
                SUMMARY_TEMPERATURE=0.3,
                SUMMARY_TIMEOUT=30,
            )
            artifacts = []
            database = types.SimpleNamespace(
                save_artifact=lambda session_id, kind, path: artifacts.append((kind, path))
            )

            def generate_text(prompt, **kwargs):
                self.assertEqual(kwargs["num_ctx"], 8192)
                self.assertEqual(kwargs["num_predict"], 2048)
                if "PROCES-VERBAL SOURCE" in prompt:
                    return "# BROUILLON - A VALIDER\n\n## Decisions prises\n- Test"
                return "# BROUILLON - A VALIDER\n\n[Intervenant_1] Decision test."

            ollama = types.SimpleNamespace(generate_text=generate_text, unload_model=lambda: "done")
            audio_preprocess = types.SimpleNamespace(
                prepare_audio=lambda session_id, folder: str(audio_path)
            )

            def run_transcription(source, folder):
                output_dir = pathlib.Path(folder) / "transcription"
                output_dir.mkdir()
                output = output_dir / "transcript.json"
                output.write_text(
                    json.dumps([{
                        "start": 0.0, "end": 1.0, "text": "Decision test."
                    }]),
                    encoding="utf-8",
                )
                return str(output)

            transcription = types.SimpleNamespace(run_transcription=run_transcription)

            def export_all(session_id, folder, merged, pv, summary):
                for name in ("pv.docx", "resume.docx"):
                    pathlib.Path(folder, "outputs", name).write_bytes(b"BROUILLON A VALIDER")

            exporter = types.SimpleNamespace(export_all=export_all)

            modules = {
                "config": config,
                "database": database,
                "ollama_client": ollama,
                "audio_preprocess": audio_preprocess,
                "transcription": transcription,
                "exporter": exporter,
            }
            with mock.patch.dict(sys.modules, modules):
                speaker_merger = load_module(
                    "speaker_merger", ROOT / "pipeline_worker" / "speaker_merger.py"
                )
                sys.modules["speaker_merger"] = speaker_merger
                pv_generator = load_module("pv_generator", ROOT / "pipeline_worker" / "pv_generator.py")
                summary_generator = load_module(
                    "summary_generator", ROOT / "pipeline_worker" / "summary_generator.py"
                )
                sys.modules["pv_generator"] = pv_generator
                sys.modules["summary_generator"] = summary_generator
                pipeline = load_module("pipeline_integration", ROOT / "pipeline_worker" / "pipeline.py")
                pipeline.run_pipeline(1, {"folder_path": "sessions/Reunion_test"})

            outputs = session / "outputs"
            self.assertIn("BROUILLON", (outputs / "pv.md").read_text(encoding="utf-8"))
            self.assertIn("BROUILLON", (outputs / "resume.md").read_text(encoding="utf-8"))
            self.assertTrue((outputs / "pv.docx").exists())
            self.assertEqual({kind for kind, _ in artifacts}, {"pv", "summary"})


if __name__ == "__main__":
    unittest.main()
