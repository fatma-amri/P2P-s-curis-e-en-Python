# p2p_secure_chat/crypto_handler.py

import os
import struct
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

# Constantes
KEY_FILE_PERMISSIONS = 0o600
KEY_FILE_NAME = "private_key.pem"
PUBLIC_KEY_FILE_NAME = "public_key.pem"
FINGERPRINT_LENGTH = 16 # Longueur du fingerprint en octets
NONCE_PREFIX_SIZE = 4  # 4 bytes for nonce prefix
NONCE_COUNTER_SIZE = 8  # 8 bytes for counter
CHACHA20_NONCE_SIZE = 12  # Total nonce size for ChaCha20Poly1305

class CryptoHandler:
    """
    Gère toutes les opérations cryptographiques :
    - Génération et stockage des clés X25519 (ECDH) et Ed25519 (Signature)
    - Échange de clés sécurisé (Handshake)
    - Dérivation de clé de session (HKDF)
    - Chiffrement/Déchiffrement des messages (ChaCha20-Poly1305)
    """

    def __init__(self, key_dir="."):
        self.key_dir = key_dir
        self.x25519_private_key = None
        self.ed25519_private_key = None
        self.session_key = None
        self.nonce_prefix = None
        self.send_counter = 0
        self.load_or_generate_keys()

    def _get_key_path(self, filename):
        """Retourne le chemin complet pour un fichier de clé."""
        return os.path.join(self.key_dir, filename)

    def _generate_keys(self):
        """Génère de nouvelles paires de clés X25519 et Ed25519."""
        self.x25519_private_key = x25519.X25519PrivateKey.generate()
        self.ed25519_private_key = ed25519.Ed25519PrivateKey.generate()
        self._save_keys()

    def _save_keys(self):
        """Sauvegarde les clés privées et publiques dans des fichiers PEM."""
        # Sauvegarde de la clé privée X25519
        x25519_pem = self.x25519_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        # Sauvegarde de la clé privée Ed25519
        ed25519_pem = self.ed25519_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Concaténer les clés privées dans un seul fichier
        private_key_path = self._get_key_path(KEY_FILE_NAME)
        with open(private_key_path, "wb") as f:
            f.write(x25519_pem)
            f.write(ed25519_pem)

        # Définir les permissions (Linux/Unix)
        try:
            os.chmod(private_key_path, KEY_FILE_PERMISSIONS)
        except OSError:
            # Peut échouer sur Windows, ignorer
            pass

        # Sauvegarde des clés publiques pour l'échange
        self._save_public_keys()

    def _save_public_keys(self):
        """Sauvegarde les clés publiques dans un fichier PEM."""
        x25519_public_key = self.x25519_private_key.public_key()
        ed25519_public_key = self.ed25519_private_key.public_key()

        x25519_pub_pem = x25519_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        ed25519_pub_pem = ed25519_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        public_key_path = self._get_key_path(PUBLIC_KEY_FILE_NAME)
        with open(public_key_path, "wb") as f:
            f.write(x25519_pub_pem)
            f.write(ed25519_pub_pem)

    def _load_keys(self):
        """Charge les clés privées et publiques depuis les fichiers."""
        private_key_path = self._get_key_path(KEY_FILE_NAME)
        
        if not os.path.exists(private_key_path):
            return False

        # Lire le fichier en mode binaire
        with open(private_key_path, "rb") as f:
            content = f.read()
        
        # Séparer les blocs PEM
        pem_blocks = []
        lines = content.decode('utf-8').split('\n')
        current_block = []
        in_block = False
        
        for line in lines:
            if line.strip().startswith("-----BEGIN"):
                if current_block and in_block:
                    pem_blocks.append("\n".join(current_block) + "\n")
                    current_block = []
                in_block = True
            
            if in_block:
                current_block.append(line)
            
            if line.strip().startswith("-----END"):
                if in_block:
                    pem_blocks.append("\n".join(current_block) + "\n")
                    current_block = []
                in_block = False

        if len(pem_blocks) < 2:
            return False

        try:
            # Tenter de charger les clés à partir des blocs
            # On suppose que le premier bloc est X25519 et le second Ed25519
            self.x25519_private_key = load_pem_private_key(pem_blocks[0].encode(), password=None)
            self.ed25519_private_key = load_pem_private_key(pem_blocks[1].encode(), password=None)
            return True
        except Exception:
            # Si le chargement échoue (mauvais format, etc.), on considère que les clés ne sont pas valides
            return False

    def load_or_generate_keys(self):
        """Charge les clés existantes ou en génère de nouvelles."""
        if not self._load_keys():
            self._generate_keys()

    def get_public_keys_bundle(self):
        """Retourne les clés publiques X25519 et Ed25519 et la signature de la clé X25519."""
        x25519_public_key = self.x25519_private_key.public_key()
        ed25519_public_key = self.ed25519_private_key.public_key()

        x25519_pub_bytes = x25519_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        ed25519_pub_bytes = ed25519_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        # Signature de la clé publique X25519 avec la clé privée Ed25519
        signature = self.ed25519_private_key.sign(x25519_pub_bytes)

        return x25519_pub_bytes, ed25519_pub_bytes, signature

    def get_fingerprint(self):
        """Calcule et retourne le fingerprint de la clé publique Ed25519."""
        ed25519_public_key = self.ed25519_private_key.public_key()
        ed25519_pub_bytes = ed25519_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        digest = hashes.Hash(hashes.SHA256())
        digest.update(ed25519_pub_bytes)
        fingerprint = digest.finalize()
        
        # Retourne le fingerprint tronqué et formaté en hexadécimal
        return fingerprint[:FINGERPRINT_LENGTH].hex()

    def derive_session_key(self, peer_x25519_pub_bytes, peer_ed25519_pub_bytes, signature):
        """
        Dérive la clé de session à partir de la clé publique X25519 du pair
        après vérification de la signature Ed25519.
        """
        try:
            # 1. Charger la clé publique Ed25519 du pair
            peer_ed25519_public_key = ed25519.Ed25519PublicKey.from_public_bytes(peer_ed25519_pub_bytes)
            
            # 2. Vérifier la signature de la clé X25519 du pair
            peer_ed25519_public_key.verify(signature, peer_x25519_pub_bytes)
            
            # 3. Effectuer l'échange de clés (ECDH)
            peer_x25519_public_key = x25519.X25519PublicKey.from_public_bytes(peer_x25519_pub_bytes)
            shared_key = self.x25519_private_key.exchange(peer_x25519_public_key)
            
            # 4. Créer un sel déterministe à partir des clés publiques Ed25519
            # Ordre lexicographique pour garantir le même sel des deux côtés
            local_ed25519_pub_bytes = self.ed25519_private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            if local_ed25519_pub_bytes < peer_ed25519_pub_bytes:
                salt_material = local_ed25519_pub_bytes + peer_ed25519_pub_bytes
            else:
                salt_material = peer_ed25519_pub_bytes + local_ed25519_pub_bytes
            
            # Hacher le matériel de sel pour obtenir un sel de 32 octets
            digest = hashes.Hash(hashes.SHA256())
            digest.update(salt_material)
            salt = digest.finalize()
            
            # 5. Dériver la clé de session avec HKDF
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32, # Clé de 256 bits pour ChaCha20Poly1305
                salt=salt,
                info=b'p2p-secure-chat-session-key'
            )
            self.session_key = hkdf.derive(shared_key)
            
            # 6. Initialiser le nonce prefix pour cette session
            self.nonce_prefix = os.urandom(NONCE_PREFIX_SIZE)
            self.send_counter = 0
            
            return True
        except Exception as e:
            # print(f"Erreur lors de la dérivation de la clé de session: {e}")
            self.session_key = None
            self.nonce_prefix = None
            self.send_counter = 0
            return False

    def encrypt_message(self, message: bytes) -> bytes:
        """Chiffre un message en utilisant ChaCha20-Poly1305."""
        if not self.session_key:
            raise ValueError("Clé de session non définie. Effectuez le handshake d'abord.")

        chacha = ChaCha20Poly1305(self.session_key)
        
        # Construire le nonce : prefix (4 bytes) || counter (8 bytes)
        # Assurer que le nonce est de 12 octets au total
        counter_bytes = struct.pack('>Q', self.send_counter)  # Big-endian 64-bit counter
        nonce = self.nonce_prefix + counter_bytes
        
        # Vérifier la taille du nonce
        if len(nonce) != CHACHA20_NONCE_SIZE:
            raise ValueError(f"Nonce size must be {CHACHA20_NONCE_SIZE} bytes")
        
        # Chiffrement et authentification (AEAD)
        ciphertext = chacha.encrypt(nonce, message, None)
        
        # Incrémenter le compteur
        self.send_counter += 1
        
        # Le format de sortie est : nonce + ciphertext + tag (le tag est inclus dans ciphertext par la lib)
        return nonce + ciphertext

    def decrypt_message(self, encrypted_message: bytes) -> bytes:
        """Déchiffre un message en utilisant ChaCha20-Poly1305."""
        if not self.session_key:
            raise ValueError("Clé de session non définie. Effectuez le handshake d'abord.")

        # Vérifier la taille minimale (nonce 12 + tag 16)
        min_size = CHACHA20_NONCE_SIZE + 16
        if len(encrypted_message) < min_size:
            raise ValueError(f"Message chiffré trop court. Minimum {min_size} bytes.")

        nonce = encrypted_message[:CHACHA20_NONCE_SIZE]
        ciphertext_with_tag = encrypted_message[CHACHA20_NONCE_SIZE:]
        
        chacha = ChaCha20Poly1305(self.session_key)
        
        # Le déchiffrement vérifie également le tag d'authentification (AEAD)
        plaintext = chacha.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext

    def is_session_active(self):
        """Vérifie si une clé de session est établie."""
        return self.session_key is not None

    def clear_session(self):
        """Efface la clé de session."""
        self.session_key = None
        self.nonce_prefix = None
        self.send_counter = 0

# Le bloc if __name__ est retiré pour éviter l'exécution lors de l'importation,
# les tests seront dans une phase dédiée.
