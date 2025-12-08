# p2p_secure_chat/file_transfer.py

import os
import json
import threading
from logger import Logger, MessageType

# Constantes
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB
CHUNK_SIZE = MessageType.MAX_CHUNK_SIZE

class FileTransferHandler:
    """
    Gère l'envoi et la réception de fichiers chiffrés.
    """

    def __init__(self, network_handler, logger: Logger, gui_callback):
        self.network = network_handler
        self.logger = logger
        self.gui_callback = gui_callback # Callback pour notifier la GUI (ex: demande de chemin de sauvegarde)
        self.receiving_file = None
        self.receiving_lock = threading.Lock()

    def send_file(self, file_path):
        """
        Envoie un fichier en le divisant en morceaux chiffrés.
        """
        if not os.path.exists(file_path):
            self.logger.log(f"Erreur: Fichier non trouvé à {file_path}", "ERROR")
            return False

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            self.logger.log(f"Erreur: Taille du fichier ({file_size} octets) dépasse la limite de {MAX_FILE_SIZE} octets.", "ERROR")
            return False

        file_name = os.path.basename(file_path)
        self.logger.log(f"Démarrage de l'envoi du fichier '{file_name}' ({file_size} octets)...", "INFO")

        try:
            # 1. Envoi du message FILE_START
            metadata = json.dumps({
                "filename": file_name,
                "filesize": file_size
            }).encode('utf-8')
            
            if not self.network.send_message(MessageType.FILE_START, metadata):
                self.logger.log("Échec de l'envoi du message FILE_START.", "ERROR")
                return False

            # 2. Envoi des morceaux (FILE_CHUNK)
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    if not self.network.send_message(MessageType.FILE_CHUNK, chunk):
                        self.logger.log("Échec de l'envoi d'un morceau de fichier.", "ERROR")
                        return False
            
            # 3. Envoi du message FILE_END
            if not self.network.send_message(MessageType.FILE_END, b''):
                self.logger.log("Échec de l'envoi du message FILE_END.", "ERROR")
                return False

            self.logger.log(f"Fichier '{file_name}' envoyé avec succès.", "SUCCESS")
            return True

        except Exception as e:
            self.logger.log(f"Erreur lors de l'envoi du fichier: {e}", "ERROR")
            return False

    def handle_incoming_message(self, msg_type, plaintext_body):
        """
        Traite les messages de transfert de fichiers reçus.
        Le corps du message est déjà déchiffré par NetworkHandler.
        """
        with self.receiving_lock:
            if msg_type == MessageType.FILE_START:
                try:
                    metadata = json.loads(plaintext_body.decode('utf-8'))
                    filename = metadata.get("filename")
                    filesize = metadata.get("filesize")

                    if filesize > MAX_FILE_SIZE:
                        self.logger.log(f"Transfert de fichier rejeté: taille ({filesize}) dépasse la limite.", "ERROR")
                        self.receiving_file = None
                        return

                    # Demander à la GUI où sauvegarder le fichier
                    # La GUI doit retourner le chemin de sauvegarde complet ou None si annulé
                    save_path = self.gui_callback("file_start", filename, filesize)
                    
                    if save_path:
                        # Valider le chemin de sauvegarde
                        try:
                            # Convertir en chemin absolu
                            save_path = os.path.abspath(save_path)
                            
                            # S'assurer que le répertoire parent existe
                            save_dir = os.path.dirname(save_path)
                            if not os.path.exists(save_dir):
                                self.logger.log(f"Le répertoire {save_dir} n'existe pas.", "ERROR")
                                self.receiving_file = None
                                return
                            
                            # Utiliser basename du filename original pour éviter path traversal
                            # si l'utilisateur n'a pas fourni un nom complet
                            safe_filename = os.path.basename(filename)
                            if not os.path.basename(save_path):
                                # Si save_path est un répertoire, utiliser le nom de fichier sécurisé
                                save_path = os.path.join(save_path, safe_filename)
                            
                            # Ouvrir le fichier pour l'écriture
                            file_handle = open(save_path, 'wb')
                            
                            self.receiving_file = {
                                "name": filename,
                                "size": filesize,
                                "path": save_path,
                                "received_bytes": 0,
                                "file_handle": file_handle
                            }
                            self.logger.log(f"Réception du fichier '{filename}' ({filesize} octets) démarrée. Sauvegarde dans {save_path}", "INFO")
                        
                        except IOError as e:
                            self.logger.log(f"Erreur d'ouverture du fichier {save_path}: {e}", "ERROR")
                            self.receiving_file = None
                        except Exception as e:
                            self.logger.log(f"Erreur de validation du chemin: {e}", "ERROR")
                            self.receiving_file = None
                    else:
                        self.logger.log(f"Réception du fichier '{filename}' annulée par l'utilisateur.", "WARNING")
                        self.receiving_file = None # Indique d'ignorer les chunks suivants

                except json.JSONDecodeError as e:
                    self.logger.log(f"Erreur de décodage JSON dans FILE_START: {e}", "ERROR")
                    self.receiving_file = None
                except Exception as e:
                    self.logger.log(f"Erreur lors du traitement de FILE_START: {e}", "ERROR")
                    self.receiving_file = None

            elif msg_type == MessageType.FILE_CHUNK:
                if not self.receiving_file:
                    self.logger.log("Chunk de fichier reçu sans transfert actif. Ignoré.", "WARNING")
                    return

                try:
                    self.receiving_file["file_handle"].write(plaintext_body)
                    self.receiving_file["received_bytes"] += len(plaintext_body)
                    
                    # Vérifier que nous ne dépassons pas la taille attendue
                    if self.receiving_file["received_bytes"] > self.receiving_file["size"]:
                        self.logger.log(f"Erreur: Taille reçue dépasse la taille attendue.", "ERROR")
                        self._cleanup_receiving_file()
                        return
                    
                    # Mise à jour de la progression (optionnel, peut être géré par la GUI)
                    progress = (self.receiving_file["received_bytes"] / self.receiving_file["size"]) * 100
                    self.logger.log(f"Progression de la réception: {progress:.2f}%", "DEBUG")

                except IOError as e:
                    self.logger.log(f"Erreur d'écriture du chunk de fichier: {e}", "ERROR")
                    self._cleanup_receiving_file()
                except Exception as e:
                    self.logger.log(f"Erreur lors de l'écriture du chunk de fichier: {e}", "ERROR")
                    self._cleanup_receiving_file()

            elif msg_type == MessageType.FILE_END:
                if not self.receiving_file:
                    self.logger.log("Message FILE_END reçu sans transfert actif. Ignoré.", "WARNING")
                    return

                if self.receiving_file["received_bytes"] == self.receiving_file["size"]:
                    self.logger.log(f"Fichier '{self.receiving_file['name']}' reçu avec succès. Fichier enregistré à: {self.receiving_file['path']}", "SUCCESS")
                    self.gui_callback("file_end", self.receiving_file['name'], self.receiving_file['path'])
                else:
                    self.logger.log(f"Erreur: Taille de fichier reçue ({self.receiving_file['received_bytes']}) ne correspond pas à la taille attendue ({self.receiving_file['size']}).", "ERROR")
                
                self._cleanup_receiving_file()

    def _cleanup_receiving_file(self):
        """Ferme le handle de fichier et réinitialise l'état de réception."""
        if self.receiving_file:
            try:
                self.receiving_file["file_handle"].close()
            except Exception:
                pass
            self.receiving_file = None

# Le bloc if __name__ est retiré pour éviter l'exécution lors de l'importation.
