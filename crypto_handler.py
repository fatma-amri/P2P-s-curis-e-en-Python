# p2p_secure_chat/crypto_handler.py

import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.hazmat.backends import default_backend

# Constantes
KEY_FILE_PERMISSIONS = 0o600
KEY_FILE_NAME = "private_key.pem"
PUBLIC_KEY_FILE_NAME = "public_key.pem"
FINGERPRINT_LENGTH = 16 # Longueur du fingerprint en octets

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

        # Lire le fichier en mode texte pour séparer les blocs PEM
        with open(private_key_path, "r") as f:
            lines = f.readlines()
        
        pem_blocks = []
        current_block = []
        in_block = False
        
        for line in lines:
            if line.strip().startswith("-----BEGIN"):
                if current_block and in_block:
                    pem_blocks.append("".join(current_block))
                    current_block = []
                in_block = True
            
            if in_block:
                current_block.append(line)
            
            if line.strip().startswith("-----END"):
                if in_block:
                    current_block.append(line) # Inclure la ligne END
                    pem_blocks.append("".join(current_block))
                    current_block = []
                in_block = False

        if len(pem_blocks) < 2:
            return False

        try:
            # Tenter de charger les clés à partir des blocs
            # On suppose que le premier bloc est X25519 et le second Ed25519
            self.x25519_private_key = load_pem_private_key(pem_blocks[0].encode(), password=None, backend=default_backend())
            self.ed25519_private_key = load_pem_private_key(pem_blocks[1].encode(), password=None, backend=default_backend())
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
        
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
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
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32, # Clé de 256 bits pour ChaCha20Poly1305
                salt=None, # Pas de sel pour la simplicité, mais un sel aléatoire est préférable
                info=b'p2p-secure-chat-session-key',
                backend=default_backend()
            )
            self.session_key = hkdf.derive(shared_key)
            return True
        except Exception as e:
            # print(f"Erreur lors de la dérivation de la clé de session: {e}")
            self.session_key = None
            return False

    def encrypt_message(self, message: bytes) -> bytes:
        """Chiffre un message en utilisant ChaCha20-Poly1305."""
        if not self.session_key:
            raise ValueError("Clé de session non définie. Effectuez le handshake d'abord.")

        chacha = ChaCha20Poly1305(self.session_key)
        nonce = os.urandom(12) # Nonce de 12 octets pour ChaCha20Poly1305
        
        # Chiffrement et authentification (AEAD)
        ciphertext = chacha.encrypt(nonce, message, None)
        
        # Le format de sortie est : nonce + ciphertext + tag (le tag est inclus dans ciphertext par la lib)
        return nonce + ciphertext

    def decrypt_message(self, encrypted_message: bytes) -> bytes:
        """Déchiffre un message en utilisant ChaCha20-Poly1305."""
        if not self.session_key:
            raise ValueError("Clé de session non définie. Effectuez le handshake d'abord.")

        # Vérifier la taille minimale (nonce 12 + tag 16)
        if len(encrypted_message) < 28:
            raise ValueError("Message chiffré trop court.")

        nonce = encrypted_message[:12]
        ciphertext_with_tag = encrypted_message[12:]
        
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

# Le bloc if __name__ est retiré pour éviter l'exécution lors de l'importation,
# les tests seront dans une phase dédiée.
