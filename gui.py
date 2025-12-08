# p2p_secure_chat/gui.py

import tkinter as tk
from tkinter import scrolledtext, simpledialog, filedialog, messagebox
import threading
import os
import time
import re
from logger import MessageType

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
        # self.network.status_callback = self.update_status
        # self.network.message_callback = self.display_message
        # self.network.file_transfer_handler.gui_callback = self.handle_file_transfer_request
        # self.network.logger.set_callback(self.display_log)
        
        # Event pour synchroniser le dialogue modal de transfert de fichier
        self.file_transfer_event = None
        self.file_transfer_result = None

        self.display_log("Application démarrée. Génération/Chargement des clés cryptographiques effectuée.", "INFO")
        self.display_log(f"Votre Fingerprint (Ed25519) est: {self.crypto.get_fingerprint()}", "SYSTEM")
        self.display_log("Veuillez démarrer l'écoute ou vous connecter à un pair.", "INFO")
        
        # Mettre à jour l'état initial de l'UI
        self._update_ui_state()
        
        # Gestion de la fermeture de la fenêtre
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- Méthodes de la GUI ---

    def on_closing(self):
        """Gère la fermeture de la fenêtre."""
        if messagebox.askokcancel("Quitter", "Voulez-vous vraiment quitter l'application ?"):
            self.network.close_connection()
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
        
        # Mettre à jour l'état de l'UI après un changement de statut
        self._update_ui_state()
    
    def _update_ui_state(self):
        """Met à jour l'état des boutons en fonction de l'état de connexion."""
        is_connected = self.network and self.network.is_connected
        has_session = self.crypto and self.crypto.is_session_active()
        is_listening = self.network and self.network.is_listening
        
        # Les boutons d'envoi sont activés uniquement si connecté avec session active
        if is_connected and has_session:
            self.send_button.config(state='normal')
            self.file_button.config(state='normal')
        else:
            self.send_button.config(state='disabled')
            self.file_button.config(state='disabled')
        
        # Les boutons de connexion sont désactivés si déjà connecté ou en écoute
        if is_connected or is_listening:
            self.listen_button.config(state='disabled')
            self.connect_button.config(state='disabled')
        else:
            self.listen_button.config(state='normal')
            self.connect_button.config(state='normal')

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
                # Valider le format IP:Port
                if ':' not in ip_port:
                    messagebox.showerror("Erreur de connexion", "Format IP:Port invalide. Format attendu: IP:Port")
                    return
                
                parts = ip_port.split(':')
                if len(parts) != 2:
                    messagebox.showerror("Erreur de connexion", "Format IP:Port invalide. Format attendu: IP:Port")
                    return
                
                ip, port_str = parts
                
                # Valider l'adresse IP (simple regex)
                ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
                if not ip_pattern.match(ip):
                    messagebox.showerror("Erreur de connexion", "Adresse IP invalide.")
                    return
                
                # Vérifier que chaque octet est dans [0, 255]
                octets = ip.split('.')
                try:
                    for octet in octets:
                        octet_val = int(octet)
                        if not (0 <= octet_val <= 255):
                            messagebox.showerror("Erreur de connexion", "Adresse IP invalide (octets doivent être entre 0 et 255).")
                            return
                except ValueError:
                    messagebox.showerror("Erreur de connexion", "Adresse IP invalide (octets doivent être numériques).")
                    return
                
                # Valider le port
                try:
                    port = int(port_str)
                    if not (1 <= port <= 65535):
                        messagebox.showerror("Erreur de connexion", "Port invalide (doit être entre 1 et 65535).")
                        return
                except ValueError:
                    messagebox.showerror("Erreur de connexion", "Port invalide (doit être un nombre).")
                    return
                
                # Exécuter l'opération réseau dans un thread séparé
                threading.Thread(target=self.network.connect_to_peer, args=(ip, port), daemon=True).start()
            except ValueError:
                messagebox.showerror("Erreur de connexion", "Format IP:Port invalide.")
            except Exception as e:
                messagebox.showerror("Erreur de connexion", f"Erreur: {e}")

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
        if not self.network.is_connected or not self.crypto.is_session_active():
            messagebox.showerror("Erreur", "Vous devez être connecté et avoir une session sécurisée active pour envoyer un fichier.")
            return

        file_path = filedialog.askopenfilename(title="Sélectionner un fichier à envoyer")
        if file_path:
            # Exécuter l'envoi de fichier dans un thread séparé
            threading.Thread(target=self.file_transfer.send_file, args=(file_path,), daemon=True).start()

    def handle_file_transfer_request(self, action, filename, size_or_path):
        """
        Callback appelé par FileTransferHandler pour gérer les requêtes de transfert.
        """
        if action == "file_start":
            # Demande de confirmation et de chemin de sauvegarde
            file_size_mb = size_or_path / (1024 * 1024)
            
            # Utiliser un Event pour synchroniser avec le thread de l'UI
            self.file_transfer_event = threading.Event()
            self.file_transfer_result = None
            
            # Programmer l'affichage du dialogue dans le thread principal
            self.after(0, self._ask_save_path_async, filename, file_size_mb)
            
            # Attendre avec timeout (30 secondes) que l'utilisateur réponde
            event_set = self.file_transfer_event.wait(timeout=30.0)
            
            if not event_set:
                # Timeout - l'utilisateur n'a pas répondu à temps
                self.display_log("Timeout lors de la demande de transfert de fichier", "WARNING")
                return None
            
            return self.file_transfer_result

        elif action == "file_end":
            # Notification de fin de transfert
            self.display_message(f"Fichier '{filename}' reçu et sauvegardé à: {size_or_path}", is_system=True)
            self.after(0, lambda: messagebox.showinfo("Transfert de fichier terminé", f"Fichier '{filename}' reçu avec succès.\nSauvegardé à: {size_or_path}"))

    def _ask_save_path_async(self, filename, file_size_mb):
        """Affiche le dialogue de sauvegarde de façon asynchrone dans le thread UI."""
        try:
            # Afficher une boîte de dialogue de confirmation
            confirm = messagebox.askyesno("Transfert de fichier entrant", 
                                          f"Le pair souhaite vous envoyer le fichier '{filename}' ({file_size_mb:.2f} MB).\n\nVoulez-vous accepter le transfert et choisir un emplacement de sauvegarde ?")
            
            if confirm:
                # Ouvrir la boîte de dialogue de sauvegarde
                save_path = filedialog.asksaveasfilename(
                    title="Enregistrer le fichier reçu",
                    initialfile=filename,
                    defaultextension=".*",
                    parent=self
                )
                self.file_transfer_result = save_path if save_path else None
            else:
                self.file_transfer_result = None
        except Exception as e:
            self.display_log(f"Erreur lors du dialogue de transfert: {e}", "ERROR")
            self.file_transfer_result = None
        finally:
            # Signaler que le résultat est disponible
            if self.file_transfer_event:
                self.file_transfer_event.set()

# Le bloc if __name__ est retiré pour éviter l'exécution lors de l'importation.
