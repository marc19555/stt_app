import keyboard
import sys
import os
import msvcrt
import tempfile
import threading

sys.path.append(os.path.dirname(__file__))
from simple_logger import setup_daily_console_log
from session_manager import SessionManager
from recorder import Recorder, has_audio_input_device
from notifier import bip_start, bip_stop, bip_error, bip_no_device
from ram_server import start_ram_server
from config import HOTKEY, MAX_RECORDING_DURATION


class SingleInstanceLock:
    def __init__(self, lock_name: str):
        self.lock_path = os.path.join(tempfile.gettempdir(), lock_name)
        self.lock_file = None

    def acquire(self) -> bool:
        self.lock_file = open(self.lock_path, "a+")
        self.lock_file.seek(0)
        try:
            msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            self.lock_file.truncate(0)
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            return True
        except OSError:
            self.lock_file.close()
            self.lock_file = None
            return False

    def release(self):
        if self.lock_file is None:
            return
        try:
            self.lock_file.seek(0)
            msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        finally:
            self.lock_file.close()
            self.lock_file = None

class HotkeyListener:
    def __init__(self):
        self.session_manager = SessionManager()
        self.recorder = None
        self.auto_stop_timer = None
        self.state_lock = threading.Lock()

    def _start_auto_stop_timer(self):
        self._cancel_auto_stop_timer()
        self.auto_stop_timer = threading.Timer(MAX_RECORDING_DURATION, self._on_max_duration_reached)
        self.auto_stop_timer.daemon = True
        self.auto_stop_timer.start()

    def _cancel_auto_stop_timer(self):
        if self.auto_stop_timer is not None:
            self.auto_stop_timer.cancel()
            self.auto_stop_timer = None

    def _stop_current_recording(self, reason=None):
        if self.session_manager.current_session_id is None or self.recorder is None:
            return False

        self._cancel_auto_stop_timer()
        self.recorder.stop()
        self.session_manager.stop_session()
        self.recorder = None

        if reason:
            print(reason)

        bip_stop()
        return True

    def _on_max_duration_reached(self):
        with self.state_lock:
            self._stop_current_recording("Duree maximale atteinte (4h) : enregistrement arrete automatiquement.")

    def _on_recording_error(self, error_message):
        with self.state_lock:
            if self.session_manager.current_session_id is not None:
                print(f"[ERREUR] Arrêt forcé de l'enregistrement en raison d'un problème matériel : {error_message}")
                self._cancel_auto_stop_timer()
                
                # Arrête la session proprement sans appeler recorder.stop() pour éviter le deadlock de thread join.
                self.session_manager.stop_session()
                self.recorder = None
                
                # Joue le signal sonore spécifique de périphérique manquant/déconnecté
                bip_no_device()

    def _on_f12(self):
        with self.state_lock:
            try:
                if self.session_manager.current_session_id is None:
                    if not has_audio_input_device():
                        print("[ERREUR] Tentative d'enregistrement sans périphérique d'entrée audio. Veuillez brancher un microphone.")
                        bip_no_device()
                        return

                    session_id = self.session_manager.start_session()
                    folder = self.session_manager.current_session_folder
                    self.recorder = Recorder(folder, session_id, on_error_callback=self._on_recording_error)
                    self.recorder.start()
                    self._start_auto_stop_timer()
                    bip_start()
                else:
                    self._stop_current_recording()
            except Exception as e:
                print(f"Erreur : {e}")
                bip_error()

    def run(self):
        print("Agent en écoute — F12 pour démarrer/arrêter")
        print(f"Arret automatique apres {MAX_RECORDING_DURATION // 3600}h d'enregistrement")
        print(" Ctrl+C pour quitter")
        keyboard.add_hotkey(HOTKEY, self._on_f12)
        keyboard.wait()

if __name__ == "__main__":
    # Active la duplication console -> fichier log journalier avant tout print.
    setup_daily_console_log("agent_windows")

    start_ram_server()

    from usb_listener import UsbListener
    UsbListener().start()

    instance_lock = SingleInstanceLock("stt_agent_windows.lock")
    if not instance_lock.acquire():
        print("Une instance de l'agent Windows est deja en cours d'execution.")
        bip_error()
        sys.exit(1)

    # Vérification du microphone au démarrage de l'agent
    if not has_audio_input_device():
        print("[ATTENTION] Aucun périphérique d'entrée audio (microphone) détecté au démarrage. Veuillez brancher un microphone.")

    try:
        listener = HotkeyListener()
        listener.run()
    finally:
        instance_lock.release()