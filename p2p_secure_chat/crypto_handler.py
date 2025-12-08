import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import serialization

# Constantes
KEY_FILE_PERMISSIONS = 0o600
KEY_FILE_NAME = "private_key.pem"
PUBLIC_KEY_FILE_NAME = "public_key.pem"
FINGERPRINT_LENGTH = 16 # Longueur du fingerprint en octets
NONCE_PREFIX_LEN = 4
NONCE_COUNTER_LEN = 8
NONCE_LEN = NONCE_PREFIX_LEN + NONCE_COUNTER_LEN

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
        # nonce_prefix et compteur d'envoi pour ChaCha20-Poly1305 (unicité)
        self.nonce_prefix = None
        self._send_counter = 0
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

        # Lire le fichier en mode binaire et séparer les blocs PEM
        with open(private_key_path, "rb") as f:
            data = f.read()

        # Séparer les blocs PEM en bytes
        pem_blocks = []
        marker_begin = b"-----BEGIN"
        marker_end = b"-----END"
        parts = data.split(marker_begin)
        for part in parts:
            if part.strip():
                block = marker_begin + part
                if marker_end in block:
                    # récupérer le bloc complet jusqu'à la ligne END
                    pem_blocks.append(block)

        if len(pem_blocks) < 2:
            return False

        try:
            # On suppose que le premier bloc est X25519 et le second Ed25519
            self.x25519_private_key = serialization.load_pem_private_key(pem_blocks[0], password=None)
            self.ed25519_private_key = serialization.load_pem_private_key(pem_blocks[1], password=None)
            return True
        except Exception:
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
            
            # 4. Dériver la clé de session avec HKDF
            # Deriver un sel déterministe à partir des clés publiques Ed25519 (pair + local)
            # Les clés doivent être triées pour garantir le même sel des deux côtés
            digest = hashes.Hash(hashes.SHA256())
            local_ed25519_pub = self.ed25519_private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            # Trier les clés pour garantir un ordre déterministe
            sorted_keys = sorted([peer_ed25519_pub_bytes, local_ed25519_pub])
            digest.update(sorted_keys[0])
            digest.update(sorted_keys[1])
            hkdf_salt = digest.finalize()

            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32, # Clé de 256 bits pour ChaCha20Poly1305
                salt=hkdf_salt,
                info=b'p2p-secure-chat-session-key'
            )
            self.session_key = hkdf.derive(shared_key)

            # Initialiser le préfixe de nonce pour éviter la réutilisation entre pairs
            # Préfixe dérivé de la clé publique Ed25519 locale (4 octets)
            prefix_digest = hashes.Hash(hashes.SHA256())
            prefix_digest.update(local_ed25519_pub)
            self.nonce_prefix = prefix_digest.finalize()[:NONCE_PREFIX_LEN]
            # Initialiser le compteur de messages à une valeur aléatoire faible (prévenir collisions après reboot)
            self._send_counter = int.from_bytes(os.urandom(NONCE_COUNTER_LEN), 'big') & ((1 << (NONCE_COUNTER_LEN*8)) - 1)

            return True
        except Exception:
            # Pas d'information détaillée renvoyée pour éviter les fuites
            self.session_key = None
            self.nonce_prefix = None
            self._send_counter = 0
            return False

    def encrypt_message(self, message: bytes) -> bytes:
        """Chiffre un message en utilisant ChaCha20-Poly1305."""
        if not self.session_key or not self.nonce_prefix:
            raise ValueError("Clé de session non définie. Effectuez le handshake d'abord.")

        # Construire un nonce unique par message basé sur un préfixe et un compteur
        counter = self._send_counter
        nonce = self.nonce_prefix + counter.to_bytes(NONCE_COUNTER_LEN, 'big')
        # Incrémenter le compteur (wrap-around géré)
        self._send_counter = (self._send_counter + 1) & ((1 << (NONCE_COUNTER_LEN*8)) - 1)

        chacha = ChaCha20Poly1305(self.session_key)
        ciphertext = chacha.encrypt(nonce, message, None)

        # Format: nonce (12) + ciphertext (inclut tag)
        return nonce + ciphertext

    def decrypt_message(self, encrypted_message: bytes) -> bytes:
        """Déchiffre un message en utilisant ChaCha20-Poly1305."""
        if not self.session_key:
            raise ValueError("Clé de session non définie. Effectuez le handshake d'abord.")

        # Vérifier la taille minimale (nonce 12 + tag 16)
        if len(encrypted_message) < NONCE_LEN + 16:
            raise ValueError("Message chiffré trop court.")

        nonce = encrypted_message[:NONCE_LEN]
        ciphertext_with_tag = encrypted_message[NONCE_LEN:]
        
        chacha = ChaCha20Poly1305(self.session_key)
        
        plaintext = chacha.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext

    def is_session_active(self):
        """Vérifie si une clé de session est établie."""
        return self.session_key is not None

    def clear_session(self):
        """Efface la clé de session."""
        self.session_key = None
        self.nonce_prefix = None
        self._send_counter = 0