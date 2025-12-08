# p2p_secure_chat/test_crypto.py

import unittest
import os
import shutil
from crypto_handler import CryptoHandler

# Répertoires temporaires pour les tests
TEST_DIR_A = "test_keys_a"
TEST_DIR_B = "test_keys_b"

class TestCryptoHandler(unittest.TestCase):
    """Tests unitaires pour la classe CryptoHandler."""

    @classmethod
    def setUpClass(cls):
        """Configuration avant l'exécution des tests."""
        if os.path.exists(TEST_DIR_A):
            shutil.rmtree(TEST_DIR_A)
        if os.path.exists(TEST_DIR_B):
            shutil.rmtree(TEST_DIR_B)
        os.makedirs(TEST_DIR_A)
        os.makedirs(TEST_DIR_B)

    @classmethod
    def tearDownClass(cls):
        """Nettoyage après l'exécution des tests."""
        if os.path.exists(TEST_DIR_A):
            shutil.rmtree(TEST_DIR_A)
        if os.path.exists(TEST_DIR_B):
            shutil.rmtree(TEST_DIR_B)

    def setUp(self):
        """Configuration avant chaque test."""
        self.crypto_a = CryptoHandler(key_dir=TEST_DIR_A)
        self.crypto_b = CryptoHandler(key_dir=TEST_DIR_B)
        self.crypto_a.clear_session()
        self.crypto_b.clear_session()

    def test_key_generation_and_loading(self):
        """Teste la génération, la sauvegarde et le chargement des clés."""
        # Vérifier que les clés ont été générées
        self.assertIsNotNone(self.crypto_a.x25519_private_key)
        self.assertIsNotNone(self.crypto_a.ed25519_private_key)

        # Vérifier que les fichiers existent pour A
        self.assertTrue(os.path.exists(os.path.join(TEST_DIR_A, "private_key.pem")))
        self.assertTrue(os.path.exists(os.path.join(TEST_DIR_A, "public_key.pem")))

        # Créer un nouveau handler pour tester le chargement (utilise le répertoire A)
        crypto_c = CryptoHandler(key_dir=TEST_DIR_A)
        self.assertIsNotNone(crypto_c.x25519_private_key)
        self.assertIsNotNone(crypto_c.ed25519_private_key)

        # Le fingerprint doit être le même
        self.assertEqual(self.crypto_a.get_fingerprint(), crypto_c.get_fingerprint())

    def test_fingerprint_generation(self):
        """Teste la génération du fingerprint."""
        fp_a = self.crypto_a.get_fingerprint()
        self.assertIsInstance(fp_a, str)
        self.assertTrue(len(fp_a) > 0)
        # Le fingerprint doit être différent pour deux instances différentes
        fp_b = self.crypto_b.get_fingerprint()
        self.assertNotEqual(fp_a, fp_b)

    def test_handshake_and_key_derivation(self):
        """Teste le handshake complet et la dérivation de clé de session."""
        # Obtenir les bundles de clés
        bundle_a = self.crypto_a.get_public_keys_bundle()
        bundle_b = self.crypto_b.get_public_keys_bundle()

        # Handshake A -> B
        success_b = self.crypto_b.derive_session_key(*bundle_a)
        self.assertTrue(success_b)
        self.assertTrue(self.crypto_b.is_session_active())

        # Handshake B -> A
        success_a = self.crypto_a.derive_session_key(*bundle_b)
        self.assertTrue(success_a)
        self.assertTrue(self.crypto_a.is_session_active())

        # Les clés de session doivent être identiques
        self.assertEqual(self.crypto_a.session_key, self.crypto_b.session_key)

    def test_handshake_failure_on_bad_signature(self):
        """Teste l'échec du handshake avec une mauvaise signature."""
        bundle_a = self.crypto_a.get_public_keys_bundle()
        
        # Modifier la signature de A
        x25519_pub_a, ed25519_pub_a, sig_a = bundle_a
        bad_sig_a = b'x' * len(sig_a) # Signature invalide

        # Handshake A -> B avec mauvaise signature
        success_b = self.crypto_b.derive_session_key(x25519_pub_a, ed25519_pub_a, bad_sig_a)
        self.assertFalse(success_b)
        self.assertFalse(self.crypto_b.is_session_active())

    def test_encryption_decryption(self):
        """Teste le chiffrement et le déchiffrement d'un message."""
        # Établir la clé de session
        bundle_a = self.crypto_a.get_public_keys_bundle()
        bundle_b = self.crypto_b.get_public_keys_bundle()
        self.crypto_b.derive_session_key(*bundle_a)
        self.crypto_a.derive_session_key(*bundle_b)

        message_clair = "Ceci est un message de test sécurisé."
        message_bytes = message_clair.encode('utf-8')

        # A chiffre
        message_chiffre = self.crypto_a.encrypt_message(message_bytes)
        
        # B déchiffre
        message_dechiffre_bytes = self.crypto_b.decrypt_message(message_chiffre)
        message_dechiffre = message_dechiffre_bytes.decode('utf-8')

        self.assertEqual(message_clair, message_dechiffre)

    def test_decryption_failure_on_tampering(self):
        """Teste l'échec du déchiffrement après altération (AEAD)."""
        # Établir la clé de session
        bundle_a = self.crypto_a.get_public_keys_bundle()
        bundle_b = self.crypto_b.get_public_keys_bundle()
        self.crypto_b.derive_session_key(*bundle_a)
        self.crypto_a.derive_session_key(*bundle_b)

        message_clair = "Message à altérer."
        message_bytes = message_clair.encode('utf-8')

        # A chiffre
        message_chiffre = self.crypto_a.encrypt_message(message_bytes)
        
        # Altération d'un octet (après le nonce de 12 octets)
        tampered_message = bytearray(message_chiffre)
        tampered_message[15] ^= 0x01
        tampered_message = bytes(tampered_message)

        # B tente de déchiffrer
        with self.assertRaises(Exception): # ChaCha20Poly1305 lève une exception en cas d'échec d'authentification
            self.crypto_b.decrypt_message(tampered_message)

if __name__ == '__main__':
    unittest.main()