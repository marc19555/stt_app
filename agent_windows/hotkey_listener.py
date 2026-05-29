import keyboard
import sys
import os

sys.path.append(os.path.dirname(__file__))
from session_manager import SessionManager
from recorder import Recorder
from notifier import bip_start, bip_stop, bip_error
from config import HOTKEY, SESSIONS_DIR

class HotkeyListener:
    def __init__(self):
        self.session_manager = SessionManager()
        self.recorder = None

    def _on_f12(self):
        try:
            if self.session_manager.current_session_id is None:
                session_id = self.session_manager.start_session()
                folder = os.path.join(SESSIONS_DIR, f"session_{session_id}")
                self.recorder = Recorder(folder, session_id)
                self.recorder.start()
                bip_start()
            else:
                self.recorder.stop()
                self.session_manager.stop_session()
                self.recorder = None
                bip_stop()
        except Exception as e:
            print(f"Erreur : {e}")
            bip_error()

    def run(self):
        print("Agent en écoute — F12 pour démarrer/arrêter")
        print(" Ctrl+C pour quitter")
        keyboard.add_hotkey(HOTKEY, self._on_f12)
        keyboard.wait()

if __name__ == "__main__":
    listener = HotkeyListener()
    listener.run()