import os
import sys
import shutil
import string
import ctypes
import threading
import time

sys.path.append(os.path.dirname(__file__))
from simple_logger import setup_daily_console_log
from config import SESSIONS_DIR, USB_TARGET_LABEL
from notifier import bip_usb_detected, bip_usb_done, bip_error

POLL_INTERVAL = 5  # secondes entre chaque vérification


def _get_drive_label(drive_letter: str) -> str | None:
    """Retourne le label de volume d'un lecteur, ou None en cas d'erreur."""
    buf = ctypes.create_unicode_buffer(1024)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(f"{drive_letter}:\\"),
        buf, ctypes.sizeof(buf),
        None, None, None, None, 0,
    )
    return buf.value if ok else None


def _get_removable_drives() -> list[str]:
    """Retourne les lettres de lecteurs amovibles présents."""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if bitmask & (1 << i):
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\")
            if drive_type == 2:  # DRIVE_REMOVABLE
                drives.append(letter)
    return drives


def _find_target_usb() -> str | None:
    """Retourne le chemin racine de la clé cible (ex: 'E:\\'), ou None."""
    for letter in _get_removable_drives():
        label = _get_drive_label(letter)
        if label and label.upper() == USB_TARGET_LABEL.upper():
            return f"{letter}:\\"
    return None


def _get_processed_sessions() -> list[tuple[str, str]]:
    """Retourne les sessions ayant au moins un .docx dans leur dossier outputs/."""
    sessions = []
    if not os.path.isdir(SESSIONS_DIR):
        return sessions
    for name in sorted(os.listdir(SESSIONS_DIR)):
        folder = os.path.join(SESSIONS_DIR, name)
        outputs = os.path.join(folder, "outputs")
        if os.path.isdir(outputs) and any(
            f.endswith(".docx") for f in os.listdir(outputs)
        ):
            sessions.append((name, outputs))
    return sessions


def _copy_to_usb(usb_root: str) -> None:
    """Copie les fichiers traités vers <usb>/STT_Sessions/ (ne réécrit pas les existants)."""
    dest_root = os.path.join(usb_root, "STT_Sessions")
    sessions = _get_processed_sessions()

    if not sessions:
        print("[USB] Aucune session traitée à copier.")
        return

    for name, outputs_src in sessions:
        dest_dir = os.path.join(dest_root, name)
        os.makedirs(dest_dir, exist_ok=True)
        for fname in os.listdir(outputs_src):
            src = os.path.join(outputs_src, fname)
            dst = os.path.join(dest_dir, fname)
            if os.path.isfile(src):
                if os.path.exists(dst):
                    print(f"[USB] Ignoré (déjà présent) : {name}/{fname}")
                else:
                    shutil.copy2(src, dst)
                    print(f"[USB] Copié : {name}/{fname}")


class UsbListener:
    """Surveille l'insertion d'une clé USB nommée USB_TARGET_LABEL et copie les sessions traitées."""

    def __init__(self):
        self._known_present = False
        self._thread: threading.Thread | None = None

    def _loop(self) -> None:
        while True:
            try:
                usb = _find_target_usb()
                if usb and not self._known_present:
                    self._known_present = True
                    print(f"[USB] Clé '{USB_TARGET_LABEL}' détectée sur {usb}")
                    bip_usb_detected()
                    try:
                        _copy_to_usb(usb)
                        bip_usb_done()
                        print("[USB] Copie terminée.")
                    except Exception as exc:
                        print(f"[USB] Erreur lors de la copie : {exc}")
                        bip_error()
                elif not usb and self._known_present:
                    self._known_present = False
                    print(f"[USB] Clé '{USB_TARGET_LABEL}' retirée.")
            except Exception as exc:
                print(f"[USB] Erreur inattendue dans la boucle : {exc}")

            time.sleep(POLL_INTERVAL)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True, name="UsbListener")
        self._thread.start()
        print(f"[USB] Listener actif — en attente de la clé '{USB_TARGET_LABEL}'")
