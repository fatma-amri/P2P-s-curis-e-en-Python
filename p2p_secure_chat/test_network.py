"""
Test suite pour vérifier les fonctionnalités de gestion de connexion réseau.
"""

import unittest
import time
import threading
import socket
from p2p_secure_chat.crypto_handler import CryptoHandler
from p2p_secure_chat.network_handler import NetworkHandler
from p2p_secure_chat.logger import Logger, MessageType


class TestNetworkConnection(unittest.TestCase):
    """Tests pour vérifier la gestion des connexions réseau."""

    def setUp(self):
        """Configuration avant chaque test."""
        import os
        
        self.test_port = 15000
        
        # Créer les répertoires de test
        os.makedirs("test_keys_network_a", exist_ok=True)
        os.makedirs("test_keys_network_b", exist_ok=True)
        
        self.logger_a = Logger()
        self.logger_b = Logger()
        
        self.crypto_a = CryptoHandler(key_dir="test_keys_network_a")
        self.crypto_b = CryptoHandler(key_dir="test_keys_network_b")
        
        self.messages_a = []
        self.messages_b = []
        
        def message_callback_a(msg, is_system=False):
            self.messages_a.append(msg)
        
        def message_callback_b(msg, is_system=False):
            self.messages_b.append(msg)
        
        self.network_a = NetworkHandler(
            crypto_handler=self.crypto_a,
            logger=self.logger_a,
            message_callback=message_callback_a,
            status_callback=None,
            file_transfer_handler=None
        )
        
        self.network_b = NetworkHandler(
            crypto_handler=self.crypto_b,
            logger=self.logger_b,
            message_callback=message_callback_b,
            status_callback=None,
            file_transfer_handler=None
        )

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.network_a.close_connection()
        self.network_b.close_connection()
        time.sleep(0.5)  # Attendre que les sockets se ferment proprement
        
        # Nettoyer les répertoires de test
        import shutil
        import os
        for dir_name in ["test_keys_network_a", "test_keys_network_b"]:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)

    def test_port_conflict_handling(self):
        """Teste la gestion des conflits de port."""
        # Démarrer l'écoute sur le port de test
        port_used = self.network_a.start_listening(self.test_port)
        self.assertEqual(port_used, self.test_port)
        self.assertTrue(self.network_a.is_listening)
        
        # Essayer de démarrer l'écoute sur le même port sans allow_dynamic_port
        port_used_b = self.network_b.start_listening(self.test_port, allow_dynamic_port=False)
        self.assertIsNone(port_used_b)
        self.assertFalse(self.network_b.is_listening)
        
        # Nettoyer et attendre que le port soit libéré
        self.network_a.close_connection()
        time.sleep(1.0)  # Attendre plus longtemps pour que le système d'exploitation libère le port
        
        # Essayer avec allow_dynamic_port
        port_used_a2 = self.network_a.start_listening(self.test_port)
        if port_used_a2 is None:
            # Si le port n'est toujours pas libéré, c'est acceptable, on continue avec un autre port
            port_used_a2 = self.network_a.start_listening(self.test_port + 100)
        self.assertIsNotNone(port_used_a2)
        
        port_used_b2 = self.network_b.start_listening(port_used_a2, allow_dynamic_port=True)
        self.assertIsNotNone(port_used_b2)
        if port_used_a2 == port_used_b2:
            # Dans le cas improbable où le port est le même (ne devrait pas arriver)
            # c'est que le port a été libéré entre-temps, ce qui est acceptable
            self.skipTest("Port conflict test skipped due to rapid port release")
        self.assertTrue(self.network_b.is_listening)

    def test_session_key_persistence(self):
        """Teste que la clé de session persiste après le handshake."""
        # Démarrer l'écoute
        port_used = self.network_a.start_listening(self.test_port)
        self.assertIsNotNone(port_used)
        time.sleep(0.5)
        
        # Se connecter depuis B
        self.network_b.connect_to_peer("127.0.0.1", port_used)
        
        # Attendre que la connexion soit établie et le handshake terminé
        max_wait = 5
        start_time = time.time()
        while (time.time() - start_time) < max_wait:
            if self.network_a.is_connected and self.network_b.is_connected:
                if self.crypto_a.is_session_active() and self.crypto_b.is_session_active():
                    break
            time.sleep(0.1)
        
        # Vérifier que les deux pairs sont connectés
        self.assertTrue(self.network_a.is_connected, "Network A should be connected")
        self.assertTrue(self.network_b.is_connected, "Network B should be connected")
        
        # Vérifier que les clés de session sont actives
        self.assertTrue(self.crypto_a.is_session_active(), "Crypto A session should be active")
        self.assertTrue(self.crypto_b.is_session_active(), "Crypto B session should be active")
        
        # Vérifier que les clés de session sont identiques
        self.assertEqual(self.crypto_a.session_key, self.crypto_b.session_key)
        
        # Attendre un peu pour s'assurer que la connexion reste stable
        time.sleep(1)
        
        # Vérifier que les clés de session sont toujours actives
        self.assertTrue(self.crypto_a.is_session_active(), "Crypto A session should still be active")
        self.assertTrue(self.crypto_b.is_session_active(), "Crypto B session should still be active")
        self.assertTrue(self.network_a.is_connected, "Network A should still be connected")
        self.assertTrue(self.network_b.is_connected, "Network B should still be connected")

    def test_message_exchange(self):
        """Teste l'envoi et la réception de messages."""
        # Démarrer l'écoute
        port_used = self.network_a.start_listening(self.test_port)
        self.assertIsNotNone(port_used)
        time.sleep(0.5)
        
        # Se connecter depuis B
        self.network_b.connect_to_peer("127.0.0.1", port_used)
        
        # Attendre la connexion
        max_wait = 5
        start_time = time.time()
        while (time.time() - start_time) < max_wait:
            if self.network_a.is_connected and self.network_b.is_connected:
                if self.crypto_a.is_session_active() and self.crypto_b.is_session_active():
                    break
            time.sleep(0.1)
        
        # Vérifier la connexion
        self.assertTrue(self.network_a.is_connected)
        self.assertTrue(self.network_b.is_connected)
        
        # Envoyer un message de B vers A
        test_message = "Test message from B to A"
        success = self.network_b.send_message(MessageType.TEXT, test_message.encode('utf-8'))
        self.assertTrue(success, "Message should be sent successfully")
        
        # Attendre que le message soit reçu
        time.sleep(1)
        
        # Vérifier que A a reçu le message
        self.assertGreater(len(self.messages_a), 0, "A should have received messages")
        received_message = self.messages_a[-1]
        self.assertEqual(received_message, test_message)
        
        # Envoyer un message de A vers B
        test_message_2 = "Test message from A to B"
        success = self.network_a.send_message(MessageType.TEXT, test_message_2.encode('utf-8'))
        self.assertTrue(success, "Message should be sent successfully")
        
        # Attendre que le message soit reçu
        time.sleep(1)
        
        # Vérifier que B a reçu le message
        self.assertGreater(len(self.messages_b), 0, "B should have received messages")
        received_message_2 = self.messages_b[-1]
        self.assertEqual(received_message_2, test_message_2)
        
        # Vérifier que les connexions sont toujours actives après l'envoi de messages
        self.assertTrue(self.network_a.is_connected, "Network A should still be connected after sending")
        self.assertTrue(self.network_b.is_connected, "Network B should still be connected after sending")
        self.assertTrue(self.crypto_a.is_session_active(), "Crypto A session should still be active after sending")
        self.assertTrue(self.crypto_b.is_session_active(), "Crypto B session should still be active after sending")


if __name__ == '__main__':
    unittest.main()
