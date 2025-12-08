# p2p_secure_chat/network_handler.py

import socket
import threading
import struct
import time
from logger import Logger, MessageType
from crypto_handler import CryptoHandler

# Constantes réseau
HEADER_SIZE = 8 # 4 bytes type + 4 bytes size
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB
RECV_BUFFER_SIZE = 4096

class NetworkHandler:
    """
    Gère toutes les opérations réseau P2P :
    - Mode serveur (écoute) et mode client (connexion)
    - Gestion des connexions avec threading
    - Handshake cryptographique
    - Envoi et réception de messages chiffrés
    """

    def __init__(self, crypto_handler: CryptoHandler, logger: Logger, message_callback, status_callback, file_transfer_handler):
        self.file_transfer_handler = file_transfer_handler
        self.crypto = crypto_handler
        self.logger = logger
        self.message_callback = message_callback # Fonction pour afficher les messages reçus
        self.status_callback = status_callback   # Fonction pour mettre à jour le statut de connexion
        
        self.server_socket = None
        self.peer_socket = None
        self.peer_addr = None
        self.is_listening = False
        self.is_connected = False
        self.rekey_counter = 0
        self.lock = threading.Lock()

    def start_listening(self, port):
        """Démarre le serveur TCP en mode écoute."""
        if self.is_listening or self.is_connected:
            self.logger.log("Le réseau est déjà actif.", "WARNING")
            return

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(1)
            self.is_listening = True
            self.status_callback("Écoute sur le port " + str(port))
            self.logger.log(f"Démarrage de l'écoute sur le port {port}...", "INFO")
            
            threading.Thread(target=self._listen_loop, daemon=True).start()
        except Exception as e:
            self.logger.log(f"Erreur lors du démarrage de l'écoute: {e}", "ERROR")
            self.status_callback("Erreur d'écoute")
            self.close_connection()

    def _listen_loop(self):
        """Boucle d'écoute du serveur pour accepter les connexions entrantes."""
        while self.is_listening:
            try:
                self.server_socket.settimeout(1) # Timeout pour permettre l'arrêt propre
                conn, addr = self.server_socket.accept()
                self.logger.log(f"Connexion entrante de {addr[0]}:{addr[1]}", "INFO")
                
                # N'accepter qu'une seule connexion P2P
                if self.is_connected:
                    self.logger.log("Connexion rejetée: une connexion est déjà active.", "WARNING")
                    conn.close()
                    continue

                self.peer_socket = conn
                self.peer_addr = addr
                self.is_connected = True
                self.status_callback(f"Connecté à {addr[0]}:{addr[1]}")
                
                # Démarrer le thread de gestion de la connexion
                threading.Thread(target=self._handle_connection, args=(conn, addr), daemon=True).start()
                self.is_listening = False # Arrêter l'écoute après la connexion
                self.server_socket.close()
                self.server_socket = None

            except socket.timeout:
                continue
            except Exception as e:
                if self.is_listening:
                    self.logger.log(f"Erreur dans la boucle d'écoute: {e}", "ERROR")
                break
        
        self.is_listening = False

    def connect_to_peer(self, ip, port):
        """Tente de se connecter à un pair en tant que client."""
        if self.is_connected or self.is_listening:
            self.logger.log("Le réseau est déjà actif.", "WARNING")
            return

        self.logger.log(f"Tentative de connexion à {ip}:{port}...", "INFO")
        self.status_callback(f"Connexion à {ip}:{port}...")
        
        try:
            self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.peer_socket.connect((ip, port))
            self.peer_addr = (ip, port)
            self.is_connected = True
            self.status_callback(f"Connecté à {ip}:{port}")
            
            # Démarrer le thread de gestion de la connexion
            threading.Thread(target=self._handle_connection, args=(self.peer_socket, self.peer_addr), daemon=True).start()

        except Exception as e:
            self.logger.log(f"Échec de la connexion à {ip}:{port}: {e}", "ERROR")
            self.status_callback("Déconnecté")
            self.close_connection()

    def _handle_connection(self, conn, addr):
        """Gère le cycle de vie d'une connexion (handshake et boucle de réception)."""
        try:
            # 1. Handshake cryptographique
            if not self._handshake(conn):
                self.logger.log("Échec du handshake cryptographique. Fermeture de la connexion.", "ERROR")
                self.close_connection()
                return

            self.logger.log("Handshake réussi. Clé de session établie.", "SUCCESS")
            self.message_callback("--- Session sécurisée établie ---", is_system=True)

            # 2. Boucle de réception des messages
            self._receive_loop(conn)

        except Exception as e:
            self.logger.log(f"Erreur de gestion de connexion avec {addr[0]}:{addr[1]}: {e}", "ERROR")
        finally:
            self.close_connection()

    def _handshake(self, conn):
        """Implémente l'échange de clés X25519 et l'authentification Ed25519."""
        try:
            # Étape 1: Envoi de nos clés publiques et signature
            x25519_pub, ed25519_pub, signature = self.crypto.get_public_keys_bundle()
            
            # Taille totale du bundle
            bundle_size = len(x25519_pub) + len(ed25519_pub) + len(signature)
            
            # Header du message HANDSHAKE
            header = struct.pack('!II', MessageType.HANDSHAKE, bundle_size)
            
            # Envoi du header et du bundle
            conn.sendall(header + x25519_pub + ed25519_pub + signature)
            self.logger.log("Clés publiques et signature envoyées.", "DEBUG")

            # Étape 2: Réception des clés publiques et signature du pair
            # Réception du header
            header_data = self._recv_all(conn, HEADER_SIZE)
            if not header_data:
                self.logger.log("Handshake échoué: réception du header.", "ERROR")
                return False
            
            msg_type, msg_size = struct.unpack('!II', header_data)
            
            if msg_type != MessageType.HANDSHAKE:
                self.logger.log(f"Handshake échoué: type de message inattendu ({msg_type}).", "ERROR")
                return False

            # Réception du bundle du pair
            bundle_data = self._recv_all(conn, msg_size)
            if not bundle_data:
                self.logger.log("Handshake échoué: réception du bundle.", "ERROR")
                return False

            # Les clés X25519 et Ed25519 ont des tailles fixes
            X25519_PUB_LEN = 32
            ED25519_PUB_LEN = 32
            
            peer_x25519_pub = bundle_data[:X25519_PUB_LEN]
            peer_ed25519_pub = bundle_data[X25519_PUB_LEN:X25519_PUB_LEN + ED25519_PUB_LEN]
            peer_signature = bundle_data[X25519_PUB_LEN + ED25519_PUB_LEN:]

            # Étape 3: Dérivation de la clé de session
            if not self.crypto.derive_session_key(peer_x25519_pub, peer_ed25519_pub, peer_signature):
                self.logger.log("Handshake échoué: échec de la vérification de signature ou de la dérivation de clé.", "ERROR")
                return False

            return True

        except Exception as e:
            self.logger.log(f"Erreur critique lors du handshake: {e}", "ERROR")
            return False

    def _recv_all(self, conn, n):
        """Reçoit exactement n octets du socket."""
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def _receive_loop(self, conn):
        """Boucle principale de réception et de traitement des messages."""
        while self.is_connected:
            try:
                # 1. Réception du header
                header_data = self._recv_all(conn, HEADER_SIZE)
                if not header_data:
                    self.logger.log("Connexion fermée par le pair.", "INFO")
                    break
                
                msg_type, msg_size = struct.unpack('!II', header_data)

                # 2. Réception du corps du message
                encrypted_body = self._recv_all(conn, msg_size)
                if not encrypted_body:
                    self.logger.log("Connexion fermée par le pair pendant la réception du corps.", "INFO")
                    break

                # 3. Traitement du message
                self._process_message(msg_type, encrypted_body)

            except socket.timeout:
                continue
            except Exception as e:
                self.logger.log(f"Erreur de réception/traitement: {e}", "ERROR")
                break
        
        self.close_connection()

    def _process_message(self, msg_type, encrypted_body):
        """Déchiffre et traite le corps du message."""
        try:
            if msg_type == MessageType.TEXT:
                plaintext_bytes = self.crypto.decrypt_message(encrypted_body)
                message = plaintext_bytes.decode('utf-8')
                self.message_callback(message, is_system=False)
                self.rekey_counter += 1
                self._check_rekey()

            elif msg_type in [MessageType.FILE_START, MessageType.FILE_CHUNK, MessageType.FILE_END]:
                # Le corps du message est déjà déchiffré
                plaintext_bytes = self.crypto.decrypt_message(encrypted_body)
                self.file_transfer_handler.handle_incoming_message(msg_type, plaintext_bytes)
                self.rekey_counter += 1
                self._check_rekey()
            
            elif msg_type == MessageType.REKEY:
                # Le pair demande un rekeying
                self.logger.log("Demande de rekeying reçue. (Non implémenté)", "WARNING")
                pass

            else:
                self.logger.log(f"Type de message inconnu: {msg_type}", "WARNING")

        except Exception as e:
            self.logger.log(f"Erreur de déchiffrement ou de traitement du message: {e}", "ERROR")

    def send_message(self, message_type, data: bytes):
        """Chiffre et envoie un message structuré."""
        if not self.is_connected or not self.crypto.is_session_active():
            self.logger.log("Impossible d'envoyer: pas de connexion ou de clé de session active.", "WARNING")
            return False

        try:
            with self.lock:
                # 1. Chiffrement du corps
                encrypted_body = self.crypto.encrypt_message(data)
                
                # 2. Construction du header
                msg_size = len(encrypted_body)
                header = struct.pack('!II', message_type, msg_size)
                
                # 3. Envoi
                self.peer_socket.sendall(header + encrypted_body)
                
                if message_type == MessageType.TEXT:
                    self.rekey_counter += 1
                    self._check_rekey()
                
                return True

        except Exception as e:
            self.logger.log(f"Erreur lors de l'envoi du message: {e}", "ERROR")
            self.close_connection()
            return False

    def _check_rekey(self):
        """Vérifie si un renouvellement de clé est nécessaire (Bonus)."""
        if self.rekey_counter >= 100:
            self.logger.log("Déclenchement du renouvellement de clé (rekeying). (Non implémenté)", "INFO")
            # TODO: Implémenter le rekeying (nouveau handshake)
            self.rekey_counter = 0

    def close_connection(self):
        """Ferme la connexion et réinitialise l'état."""
        with self.lock:
            if self.server_socket:
                try:
                    self.server_socket.close()
                except Exception:
                    pass
                self.server_socket = None
            
            if self.peer_socket:
                try:
                    self.peer_socket.close()
                except Exception:
                    pass
                self.peer_socket = None

            self.is_listening = False
            self.is_connected = False
            self.peer_addr = None
            self.crypto.clear_session()
            self.rekey_counter = 0
            self.status_callback("Déconnecté")
            self.logger.log("Connexion fermée.", "INFO")

# Le bloc if __name__ est retiré pour éviter l'exécution lors de l'importation.
