import tkinter as tk
from tkinter import scrolledtext, simpledialog, filedialog, messagebox
import threading
import os
import time
from .logger import MessageType

# Définition des couleurs pour l'interface
COLOR_PRIMARY = "#4CAF50"  # Vert pour les boutons
COLOR_SECONDARY = "#2196F3" # Bleu pour le statut
COLOR_BACKGROUND = "#F5F5F5" # Gris clair
COLOR_TEXT = "#333333"
COLOR_SUCCESS = "#4CAF50"
COLOR_ERROR = "#F44336"

class ChatApp(tk.Tk):
    """
    Interface graphique Tkinter pour l'application de messagerie P2P sécurisée.
    """
    def __init__(self, crypto_handler, network_handler, file_transfer_handler):
        super().__init__()
        self.crypto = crypto_handler
        self.network = network_handler
        self.file_transfer = file_transfer_handler

        self.title("P2P Secure Chat - Manus")
        self.geometry("800x600")
        self.configure(bg=COLOR_BACKGROUND)

        # Configuration de la grille principale
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # --- Zone d'affichage des messages (Log/Chat) ---
        self.chat_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_frame.grid_rowconfigure(0, weight=1)

        self.chat_area = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, state='disabled', 
                                                   bg="white", fg=COLOR_TEXT, font=("Arial", 10))
        self.chat_area.grid(row=0, column=0, sticky="nsew")
        
        # Définition des tags pour la coloration
        self.chat_area.tag_config('INFO', foreground='blue')
        self.chat_area.tag_config('ERROR', foreground='red')
        self.chat_area.tag_config('WARNING', foreground='orange')
        self.chat_area.tag_config('SUCCESS', foreground=COLOR_SUCCESS)
        self.chat_area.tag_config('SYSTEM', foreground='purple', font=("Arial", 10, "bold"))
        self.chat_area.tag_config('SENT', foreground='darkgreen')
        self.chat_area.tag_config('RECEIVED', foreground='darkblue')

        # --- Zone de contrôle et de saisie ---
        self.control_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.control_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.control_frame.grid_columnconfigure(0, weight=1) # Champ de saisie
        self.control_frame.grid_columnconfigure(1, weight=0) # Boutons

        # Champ de saisie
        self.message_entry = tk.Entry(self.control_frame, font=("Arial", 10), bg="white", fg=COLOR_TEXT)
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.message_entry.bind("<Return>", lambda event: self.send_message())

        # Boutons
        self.send_button = tk.Button(self.control_frame, text="Envoyer message", command=self.send_message, 
                                     bg=COLOR_PRIMARY, fg="white", activebackground=COLOR_PRIMARY, relief=tk.FLAT)
        self.send_button.grid(row=0, column=1, padx=(5, 5), sticky="e")

        self.file_button = tk.Button(self.control_frame, text="Envoyer fichier", command=self.send_file_dialog, 
                                     bg=COLOR_PRIMARY, fg="white", activebackground=COLOR_PRIMARY, relief=tk.FLAT)
        self.file_button.grid(row=0, column=2, padx=(5, 0), sticky="e")

        # --- Zone de statut et de connexion ---
        self.status_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.status_frame.grid_columnconfigure(0, weight=1)

        # Indicateur de statut
        self.status_label = tk.Label(self.status_frame, text="Statut: Déconnecté", 
                                     bg=COLOR_BACKGROUND, fg=COLOR_ERROR, font=("Arial", 10, "bold"))
        self.status_label.grid(row=0, column=0, sticky="w")

        # Fingerprint
        self.fingerprint_label = tk.Label(self.status_frame, text=f"Fingerprint: {self.crypto.get_fingerprint()}", 
                                          bg=COLOR_BACKGROUND, fg=COLOR_TEXT, font=("Arial", 8))
        self.fingerprint_label.grid(row=1, column=0, sticky="w")

        # Boutons de connexion
        self.listen_button = tk.Button(self.status_frame, text="Démarrer écoute", command=self.start_listening_dialog, 
                                       bg=COLOR_SECONDARY, fg="white", activebackground=COLOR_SECONDARY, relief=tk.FLAT)
        self.listen_button.grid(row=0, column=1, padx=(5, 5), sticky="e")

        self.connect_button = tk.Button(self.status_frame, text="Se connecter", command=self.connect_to_peer_dialog, 
                                        bg=COLOR_SECONDARY, fg="white", activebackground=COLOR_SECONDARY, relief=tk.FLAT)
        self.connect_button.grid(row=0, column=2, padx=(5, 0), sticky="e")

        # Initialisation des callbacks pour les autres modules
        # Les callbacks seront définis dans main.py pour éviter les dépendances circulaires

        self.display_log("Application démarrée. Génération/Chargement des clés cryptographiques effectuée.", "INFO")
        self.display_log(f"Votre Fingerprint (Ed25519) est: {self.crypto.get_fingerprint()}", "SYSTEM")
        self.display_log("Veuillez démarrer l'écoute ou vous connecter à un pair.", "INFO")
        
        # Gestion de la fermeture de la fenêtre
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Désactiver certaines actions jusqu'à connexion
        self._update_ui_state()

    # --- Méthodes de la GUI ---

    def on_closing(self):
        """Gère la fermeture de la fenêtre."""
        if messagebox.askokcancel("Quitter", "Voulez-vous vraiment quitter l'application ?"):
            try:
                if self.network:
                    self.network.close_connection()
            except Exception:
                pass
            self.destroy()

    def display_log(self, message, level="INFO"):
        """Affiche un message de journalisation dans la zone de chat."""
        # Utiliser after pour garantir l'exécution dans le thread principal de Tkinter
        self.after(0, self._display_log_thread_safe, message, level)

    def _display_log_thread_safe(self, message, level):
        """Méthode thread-safe pour afficher le log."""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n", level)
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def display_message(self, message, is_system=False, is_sent=False):
        """Affiche un message de chat dans la zone de chat."""
        self.after(0, self._display_message_thread_safe, message, is_system, is_sent)

    def _display_message_thread_safe(self, message, is_system, is_sent):
        """Méthode thread-safe pour afficher le message."""
        timestamp = time.strftime("[%H:%M:%S]")
        
        if is_system:
            tag = 'SYSTEM'
            prefix = ""
        elif is_sent:
            tag = 'SENT'
            prefix = "Moi: "
        else:
            tag = 'RECEIVED'
            prefix = "Pair: "

        full_message = f"{timestamp} {prefix}{message}\n"
        
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, full_message, tag)
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def update_status(self, status_text):
        """Met à jour l'indicateur de statut de connexion."""
        self.after(0, self._update_status_thread_safe, status_text)

    def _update_status_thread_safe(self, status_text):
        """Méthode thread-safe pour mettre à jour le statut."""
        self.status_label.config(text=f"Statut: {status_text}")
        if "Connecté" in status_text:
            self.status_label.config(fg=COLOR_SUCCESS)
        elif "Déconnecté" in status_text or "Erreur" in status_text:
            self.status_label.config(fg=COLOR_ERROR)
        else:
            self.status_label.config(fg=COLOR_TEXT)
        # Mettre à jour l'état des boutons en fonction
        self._update_ui_state()

    def _update_ui_state(self):
        """Activer/désactiver des widgets selon l'état de la connexion/session."""
        connected = getattr(self.network, "is_connected", False)
        session_active = getattr(self.crypto, "is_session_active", lambda: False)()
        # Envoi de fichier seulement si connecté et session active
        if connected and session_active:
            self.file_button.config(state='normal')
        else:
            self.file_button.config(state='disabled')
        # Envoi de message si connecté et session active
        if connected and session_active:
            self.send_button.config(state='normal')
            self.message_entry.config(state='normal')
        else:
            self.send_button.config(state='disabled')
            self.message_entry.config(state='disabled')

    # --- Dialogues et Actions ---

    def start_listening_dialog(self):
        """Ouvre une boîte de dialogue pour le port d'écoute."""
        port = simpledialog.askinteger("Démarrer écoute", "Entrez le port d'écoute (ex: 5000):", parent=self, minvalue=1024, maxvalue=65535)
        if port is not None:
            # Exécuter l'opération réseau dans un thread séparé
            threading.Thread(target=self.network.start_listening, args=(port,), daemon=True).start()

    def connect_to_peer_dialog(self):
        """Ouvre une boîte de dialogue pour l'IP et le port du pair."""
        ip_port = simpledialog.askstring("Se connecter", "Entrez IP:Port du pair (ex: 127.0.0.1:5000):", parent=self)
        if ip_port:
            try:
                ip, port_str = ip_port.split(':')
                port = int(port_str)
                # Valider IP/Port minimalement
                # (Format simple, la validation complète d'IP est laissée au socket.connect)
                if port < 1 or port > 65535:
                    raise ValueError("Port hors intervalle valide")
                threading.Thread(target=self.network.connect_to_peer, args=(ip, port), daemon=True).start()
            except ValueError:
                messagebox.showerror("Erreur de connexion", "Format IP:Port invalide.")

    def send_message(self):
        """Envoie le message saisi dans le champ de saisie."""
        message = self.message_entry.get()
        if not message:
            return

        message_bytes = message.encode('utf-8')
        
        # Exécuter l'envoi dans un thread séparé pour ne pas bloquer la GUI
        threading.Thread(target=self._send_message_thread, args=(message, message_bytes), daemon=True).start()

    def _send_message_thread(self, message, message_bytes):
        """Thread pour l'envoi de message."""
        if self.network.send_message(MessageType.TEXT, message_bytes):
            self.display_message(message, is_sent=True)
            self.message_entry.after(0, lambda: self.message_entry.delete(0, tk.END)) # Thread-safe clear
        else:
            self.display_log("Échec de l'envoi du message.", "ERROR")

    def send_file_dialog(self):
        """Ouvre une boîte de dialogue pour sélectionner un fichier à envoyer."""
        if not getattr(self.network, "is_connected", False) or not self.crypto.is_session_active():
            messagebox.showerror("Erreur", "Vous devez être connecté et avoir une session sécurisée active pour envoyer un fichier.")
            return

        file_path = filedialog.askopenfilename(title="Sélectionner un fichier à envoyer")
        if file_path:
            # Exécuter l'envoi de fichier dans un thread séparé
            threading.Thread(target=self.file_transfer.send_file, args=(file_path,), daemon=True).start()

    def handle_file_transfer_request(self, action, filename, size_or_path):
        """
        Callback appelé par FileTransferHandler pour gérer les requêtes de transfert.
        Doit être thread-safe : appelé depuis le thread réseau.
        """
        if action == "file_start":
            file_size_mb = size_or_path / (1024 * 1024)
            result_container = {"path": None}
            done_event = threading.Event()

            def ask_and_store():
                try:
                    result_container["path"] = self._ask_save_path(filename, file_size_mb)
                finally:
                    done_event.set()

            # Planifier l'exécution de la boîte de dialogue dans le thread Tk
            self.after(0, ask_and_store)

            # Attendre la réponse avec un timeout raisonnable
            if done_event.wait(timeout=300):  # 5 minutes max
                return result_container["path"]
            else:
                # Timeout, considérer comme refus
                return None

        elif action == "file_end":
            # Notification de fin de transfert
            self.display_message(f"Fichier '{filename}' reçu et sauvegardé à: {size_or_path}", is_system=True)
            self.after(0, lambda: messagebox.showinfo("Transfert de fichier terminé", f"Fichier '{filename}' reçu avec succès.\nSauvegardé à: {size_or_path}"))

    def _ask_save_path(self, filename, file_size_mb):
        """Ouvre la boîte de dialogue de sauvegarde (doit être appelé dans le thread principal)."""
        
        # Afficher une boîte de dialogue de confirmation
        confirm = messagebox.askyesno("Transfert de fichier entrant", 
                                      f"Le pair souhaite vous envoyer le fichier '{filename}' ({file_size_mb:.2f} MB).\n\nVoulez-vous accepter le transfert et choisir un emplacement de sauvegarde ?")
        
        if confirm:
            # Ouvrir la boîte de dialogue de sauvegarde
            save_path = filedialog.asksaveasfilename(
                title="Enregistrer le fichier reçu",
                initialfile=os.path.basename(filename),
                defaultextension=".*",
                parent=self
            )
            return save_path
        else:
            return None