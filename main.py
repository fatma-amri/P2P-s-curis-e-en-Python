# p2p_secure_chat/main.py

import sys
import os
import threading
import time


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_handler import CryptoHandler
from network_handler import NetworkHandler
from file_transfer import FileTransferHandler
from logger import Logger
from gui import ChatApp

def main():
    """
    Point d'entrée principal de l'application.
    Initialise les modules et démarre l'interface graphique.
    """
    
    # 1. Initialisation des modules
    
    # Le répertoire des clés est le répertoire courant
    crypto_handler = CryptoHandler(key_dir=".")
    
    # Le logger est initialisé sans callback pour l'instant
    logger = Logger()
    
    # 2. Initialisation de la GUI (avec références aux handlers)
    # On passe None pour les handlers réseau et fichier pour l'instant
    # car ils ont besoin d'être initialisés avec des références croisées.
    app = ChatApp(crypto_handler, None, None)
    
    # 3. Initialisation des handlers réseau et fichier
    # On passe les callbacks de la GUI au NetworkHandler et FileTransferHandler
    file_transfer_handler = FileTransferHandler(None, logger, app.handle_file_transfer_request)
    network_handler = NetworkHandler(
        crypto_handler=crypto_handler, 
        logger=logger, 
        message_callback=app.display_message, 
        status_callback=app.update_status,
        file_transfer_handler=file_transfer_handler
    )
    
    # 4. Mise à jour des références croisées
    file_transfer_handler.network = network_handler
    app.network = network_handler
    app.file_transfer = file_transfer_handler
    logger.set_callback(app.display_log) # Le logger utilise maintenant la GUI
    
    # 5. Démarrage de l'application Tkinter
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("Arrêt de l'application...")
    finally:
        # Assurer la fermeture propre de la connexion réseau
        network_handler.close_connection()

if __name__ == "__main__":
    # S'assurer que le répertoire de travail est le répertoire du script
    # Ceci est important pour la gestion des fichiers de clés
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    main()
