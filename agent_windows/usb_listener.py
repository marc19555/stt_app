import ctypes
import hashlib
import os
import shutil
import string
import subprocess
import sys
import threading
import time

sys.path.append(os.path.dirname(__file__))
from config import (
    SESSIONS_DIR,
    USB_REQUIRE_BITLOCKER,
    USB_SECRET,
    USB_SECRET_FILE,
    USB_TARGET_LABEL,
    USB_VOLUME_SERIAL,
)
from notifier import bip_error, bip_usb_detected, bip_usb_done

POLL_INTERVAL = 5
COPY_SUFFIXES = {".docx"}


def _get_volume_info(drive_letter):
    label = ctypes.create_unicode_buffer(1024)
    serial = ctypes.c_uint(0)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(f"{drive_letter}:\\"),
        label,
        ctypes.sizeof(label),
        ctypes.byref(serial),
        None,
        None,
        None,
        0,
    )
    if not ok:
        return None, None
    return label.value, f"{serial.value:08X}"


def _get_removable_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for index, letter in enumerate(string.ascii_uppercase):
        if bitmask & (1 << index):
            if ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\") == 2:
                drives.append(letter)
    return drives


def _has_expected_secret(root):
    try:
        with open(os.path.join(root, USB_SECRET_FILE), encoding="utf-8") as handle:
            value = handle.read().strip()
        return bool(USB_SECRET) and value == USB_SECRET
    except OSError:
        return False


def _is_bitlocker_protected(root):
    if not USB_REQUIRE_BITLOCKER:
        return True
    mount_point = root[:2]
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        f"(Get-BitLockerVolume -MountPoint '{mount_point}').ProtectionStatus.ToString()",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        return result.returncode == 0 and result.stdout.strip().lower() == "on"
    except (OSError, subprocess.SubprocessError):
        return False


def _find_target_usb():
    """Valide type amovible, label, numero de volume, secret et BitLocker."""
    for letter in _get_removable_drives():
        label, serial = _get_volume_info(letter)
        if not label or label.upper() != USB_TARGET_LABEL.upper():
            continue
        if serial != USB_VOLUME_SERIAL:
            continue
        root = f"{letter}:\\"
        if not _has_expected_secret(root):
            continue
        if not _is_bitlocker_protected(root):
            print(f"[USB] Cle refusee sur {root}: BitLocker absent ou non verifiable")
            continue
        return root
    return None


def _get_processed_sessions():
    sessions = []
    if not os.path.isdir(SESSIONS_DIR):
        return sessions
    for name in sorted(os.listdir(SESSIONS_DIR)):
        folder = os.path.join(SESSIONS_DIR, name)
        outputs = os.path.join(folder, "outputs")
        if os.path.isdir(outputs) and any(
            os.path.splitext(filename)[1].lower() in COPY_SUFFIXES
            for filename in os.listdir(outputs)
        ):
            sessions.append((name, outputs))
    return sessions


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_copy(source, destination):
    if os.path.exists(destination) and _sha256(source) == _sha256(destination):
        return "deja_verifie"
    temporary = destination + ".part"
    shutil.copy2(source, temporary)
    if _sha256(source) != _sha256(temporary):
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise IOError(f"Echec de verification SHA-256 pour {os.path.basename(source)}")
    os.replace(temporary, destination)
    return "copie_verifiee"


def _copy_to_usb(usb_root):
    sessions = _get_processed_sessions()
    if not sessions:
        print("[USB] Aucun document a copier")
        return
    destination_root = os.path.join(usb_root, "STT_Sessions")
    for name, source_dir in sessions:
        destination_dir = os.path.join(destination_root, name)
        os.makedirs(destination_dir, exist_ok=True)
        for filename in os.listdir(source_dir):
            if os.path.splitext(filename)[1].lower() not in COPY_SUFFIXES:
                continue
            source = os.path.join(source_dir, filename)
            destination = os.path.join(destination_dir, filename)
            if os.path.isfile(source):
                status = _verified_copy(source, destination)
                print(f"[USB] {status}: {name}/{filename}")


class UsbListener:
    def __init__(self):
        self._known_present = False
        self._thread = None

    def _loop(self):
        while True:
            try:
                usb = _find_target_usb()
                if usb and not self._known_present:
                    self._known_present = True
                    print(f"[USB] Cle securisee detectee sur {usb}")
                    bip_usb_detected()
                    try:
                        _copy_to_usb(usb)
                        bip_usb_done()
                    except Exception as exc:
                        print(f"[USB] Copie refusee: {exc}")
                        bip_error()
                elif not usb and self._known_present:
                    self._known_present = False
                    print("[USB] Cle retiree")
            except Exception as exc:
                print(f"[USB] Controle impossible: {exc}")
            time.sleep(POLL_INTERVAL)

    def start(self):
        if not USB_VOLUME_SERIAL or not USB_SECRET:
            print("[USB] Export desactive: lancez scripts/configure-usb.ps1")
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="UsbListener")
        self._thread.start()
        print("[USB] Listener securise actif")
