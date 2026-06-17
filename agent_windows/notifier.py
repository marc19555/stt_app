import winsound
import sys
import os

sys.path.append(os.path.dirname(__file__))
from config import BIP_START_FREQ, BIP_START_DUR, BIP_STOP_FREQ, BIP_STOP_DUR

def bip_start():
    """Bip aigu = enregistrement démarré"""
    winsound.Beep(BIP_START_FREQ, BIP_START_DUR)

def bip_stop():
    """Double bip grave = enregistrement arrêté"""
    winsound.Beep(BIP_STOP_FREQ, BIP_STOP_DUR)
    winsound.Beep(BIP_STOP_FREQ, BIP_STOP_DUR)

def bip_error():
    """Triple bip grave = erreur"""
    for _ in range(3):
        winsound.Beep(300, 200)

def bip_usb_detected():
    """Triple bip monté = clé USB détectée"""
    for freq in (600, 800, 1000):
        winsound.Beep(freq, 150)

def bip_usb_done():
    """Double bip = copie USB terminée"""
    winsound.Beep(1000, 200)
    winsound.Beep(1200, 300)

def bip_no_device():
    """Son d'avertissement explicite pour périphérique audio manquant/déconnecté"""
    for _ in range(2):
        winsound.Beep(800, 150)
        winsound.Beep(400, 150)