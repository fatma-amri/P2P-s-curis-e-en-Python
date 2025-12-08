import datetime

class Logger:
    """
    Classe simple pour la journalisation des événements.
    Envoie les messages à une fonction de rappel (callback) pour l'affichage dans l'interface.
    """
    def __init__(self, callback=None):
        self.callback = callback

    def log(self, message, level="INFO"):
        """Journalise un message avec un horodatage et un niveau."""
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{timestamp} [{level}] {message}"
        
        if self.callback:
            # Passer le message et le niveau à la callback (ex: GUI attend (message, level))
            try:
                self.callback(log_message, level)
            except TypeError:
                # Compatibilité si la callback n'attend qu'un seul argument
                self.callback(log_message)
        else:
            print(log_message)

    def set_callback(self, callback):
        """Définit la fonction de rappel pour l'affichage dans l'interface."""
        self.callback = callback

# Définition des types de messages pour le protocole
class MessageType:
    HANDSHAKE = 1
    TEXT = 2
    FILE_START = 3
    FILE_CHUNK = 4
    FILE_END = 5
    REKEY = 6
    # Taille maximale d'un message (header + données chiffrées)
    MAX_MESSAGE_SIZE = 4096 
    # Taille maximale d'un chunk de fichier (pour le corps du message)
    MAX_CHUNK_SIZE = MAX_MESSAGE_SIZE - 100 # Laisser de la place pour le header et le nonce/tag