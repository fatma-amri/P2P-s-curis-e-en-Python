# P2P Secure Chat - Application de Messagerie Sécurisée

Ceci est une application de messagerie Peer-to-Peer (P2P) sécurisée développée en Python, utilisant la bibliothèque `cryptography` pour un chiffrement de bout en bout robuste et `Tkinter` pour l'interface graphique.

## Fonctionnalités

*   **Architecture P2P** : Connexion directe entre deux utilisateurs (mode serveur ou client) via TCP.
*   **Cryptographie Avancée** :
    *   Échange de clés sécurisé avec **X25519** (ECDH).
    *   Authentification des pairs avec **Ed25519** pour prévenir les attaques Man-in-the-Middle (MITM).
    *   Chiffrement des messages avec **ChaCha20-Poly1305** (AEAD).
    *   Dérivation de clé de session avec **HKDF**.
*   **Interface Utilisateur** : Interface graphique simple et ergonomique basée sur Tkinter.
*   **Transfert de Fichiers** : Envoi et réception de fichiers chiffrés (limite de 10 MB).
*   **Gestion des Clés** : Génération et stockage sécurisé des clés privées.

## Structure du Projet

Le projet est organisé en modules pour une meilleure maintenabilité :

| Fichier | Description |
| :--- | :--- |
| `main.py` | Point d'entrée de l'application, initialise et connecte tous les modules. |
| `crypto_handler.py` | Gestion de la cryptographie (génération de clés, handshake, chiffrement/déchiffrement). |
| `network_handler.py` | Gestion des connexions réseau (écoute, connexion, envoi/réception de paquets). |
| `file_transfer.py` | Logique d'envoi et de réception de fichiers par morceaux. |
| `gui.py` | Implémentation de l'interface graphique Tkinter. |
| `logger.py` | Module de journalisation simple avec support pour la GUI. |
| `requirements.txt` | Liste des dépendances Python. |
| `test_crypto.py` | Tests unitaires pour les fonctions cryptographiques. |

## Installation

### Prérequis

Vous devez avoir **Python 3.8+** installé sur votre système.

### Dépendances Python

1.  Clonez le dépôt ou téléchargez les fichiers du projet.
2.  Naviguez jusqu'au répertoire du projet.
3.  Installez les dépendances Python en utilisant `pip` :

    ```bash
    pip install -r requirements.txt
    ```

### Dépendance Tkinter (Linux)

Sur certaines distributions Linux, vous pourriez avoir besoin d'installer le paquet Tkinter séparément :

```bash
sudo apt-get install python3-tk
```

## Utilisation

### 1. Démarrage de l'application

Exécutez le fichier `main.py` :

```bash
python3 main.py
```

### 2. Échange de Clés et Authentification

Au démarrage, l'application génère ou charge vos clés privées et affiche votre **Fingerprint** (empreinte de la clé publique Ed25519).

**Avant de communiquer, vous devez vérifier manuellement le Fingerprint de votre pair.**

### 3. Connexion

L'application fonctionne en mode P2P. Un utilisateur doit démarrer l'écoute (mode serveur) et l'autre doit se connecter (mode client).

#### Mode Serveur (Écoute)

1.  Cliquez sur le bouton **"Démarrer écoute"**.
2.  Entrez le port sur lequel vous souhaitez écouter (ex: `5000`).
3.  L'application attendra une connexion entrante.

#### Mode Client (Connexion)

1.  Cliquez sur le bouton **"Se connecter"**.
2.  Entrez l'adresse IP et le port de votre pair (ex: `192.168.1.10:5000`).
3.  Une fois la connexion établie, le **Handshake Cryptographique** (échange de clés X25519 et vérification de signature Ed25519) est effectué automatiquement.
4.  Le statut passera à **"Connecté à [IP:Port]"** si le handshake réussit.

### 4. Messagerie

*   **Messages Texte** : Entrez votre message dans le champ de saisie et cliquez sur **"Envoyer message"** ou appuyez sur `Entrée`. Les messages sont chiffrés avec ChaCha20-Poly1305 avant l'envoi.
*   **Transfert de Fichiers** : Cliquez sur **"Envoyer fichier"** pour sélectionner un fichier. Le fichier sera divisé en morceaux, chiffré et envoyé. Le pair sera invité à accepter et choisir un emplacement de sauvegarde.

## Exécution des Tests Unitaires

Pour vérifier le bon fonctionnement des fonctions cryptographiques, exécutez les tests unitaires :

```bash
python3 -m unittest test_crypto.py
```

Tous les tests devraient passer (`OK`).

---
*Développé par **Manus AI***
