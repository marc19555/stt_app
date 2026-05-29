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