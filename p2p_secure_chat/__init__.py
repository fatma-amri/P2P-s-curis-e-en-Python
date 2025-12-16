"""
P2P Secure Chat - Application de messagerie sécurisée peer-to-peer

Ce package contient tous les modules nécessaires pour l'application de chat sécurisé P2P.
"""

__version__ = "1.0.0"
__author__ = "Manus AI"

# Exporter les classes principales pour un accès facile
from .crypto_handler import CryptoHandler
from .network_handler import NetworkHandler
from .file_transfer import FileTransferHandler
from .logger import Logger, MessageType

__all__ = [
    'CryptoHandler',
    'NetworkHandler',
    'FileTransferHandler',
    'Logger',
    'MessageType',
]

# GUI is optional and loaded on demand
try:
    from .gui import ChatApp
    __all__.append('ChatApp')
except ImportError:
    # tkinter may not be available in all environments
    pass
