import os
import sys
import threading
import asyncio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import engine

class UCDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UC Drive Downloader v1.0")
        self.geometry("740x580")
        self.minsize(680, 500)
        self.configure(bg="#121316")

        # Set taskbar icon if available
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self.default_dest = os.path.join(os.path.expanduser("~"), "Downloads")
        self.dest_folder = tk.StringVar(value=self.default_dest)
        self.url_var = tk.StringVar(value="")
        self.download_type = tk.StringVar(value="zip")

        self.setup_ui()
        self.update_session_badge()

    def setup_ui(self):
        # Header Frame
        header = tk.Frame(self, bg="#1a1b1f", pady=15, padx=20)
        header.pack(fill="x")

        title_lbl = tk.Label(
            header,
            text="⚡ UC DRIVE CLOUD DOWNLOADER",
            font=("Segoe UI", 16, "bold"),
            fg="#00d26a",
            bg="#1a1b1f"
        )
        title_lbl.pack(side="left")

        self.badge_lbl = tk.Label(
            header,
            text="⚪ Verificando sesión...",
            font=("Segoe UI", 9, "bold"),
            fg="#e0e0e0",
            bg="#26282f",
            padx=10,
            pady=4
        )
        self.badge_lbl.pack(side="right")

        # Main Container
        main = tk.Frame(self, bg="#121316", padx=25, pady=15)
        main.pack(fill="both", expand=True)

        # Session connection banner
        sess_frame = tk.Frame(main, bg="#1c1e24", padx=15, pady=10)
        sess_frame.pack(fill="x", pady=(0, 15))

        sess_info = tk.Label(
            sess_frame,
            text="Inicia sesión una sola vez para que el programa pueda descargar carpetas completas:",
            font=("Segoe UI", 9),
            fg="#9aa0a6",
            bg="#1c1e24"
        )
        sess_info.pack(side="left")

        self.btn_login = tk.Button(
            sess_frame,
            text="🔑 Conectar / Iniciar Sesión",
            command=self.on_login_click,
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#7b2cbf",
            activebackground="#9d4edd",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2"
        )
        self.btn_login.pack(side="right")

        # URL Input Section
        url_lbl = tk.Label(
            main,
            text="ENLACE DE UC DRIVE (uc-share.com / drive.ucweb.com):",
            font=("Segoe UI", 9, "bold"),
            fg="#9aa0a6",
            bg="#121316"
        )
        url_lbl.pack(anchor="w", pady=(0, 5))

        url_entry = tk.Entry(
            main,
            textvariable=self.url_var,
            font=("Segoe UI", 11),
            bg="#1f2127",
            fg="#ffffff",
            insertbackground="#00d26a",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2e313b",
            highlightcolor="#00d26a"
        )
        url_entry.pack(fill="x", ipady=8, pady=(0, 15))

        # Output Folder Section
        folder_lbl = tk.Label(
            main,
            text="CARPETA DE DESTINO:",
            font=("Segoe UI", 9, "bold"),
            fg="#9aa0a6",
            bg="#121316"
        )
        folder_lbl.pack(anchor="w", pady=(0, 5))

        folder_box = tk.Frame(main, bg="#121316")
        folder_box.pack(fill="x", pady=(0, 15))

        folder_entry = tk.Entry(
            folder_box,
            textvariable=self.dest_folder,
            font=("Segoe UI", 10),
            bg="#1f2127",
            fg="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2e313b"
        )
        folder_entry.pack(side="left", fill="x", expand=True, ipady=6)

        btn_browse = tk.Button(
            folder_box,
            text="📁 Cambiar",
            command=self.browse_folder,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#2a2c34",
            activebackground="#363942",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_browse.pack(side="right", padx=(8, 0))

        # Format Options & Download Button
        action_box = tk.Frame(main, bg="#121316")
        action_box.pack(fill="x", pady=(0, 15))

        opt_zip = tk.Radiobutton(
            action_box,
            text="Guardar en archivo .ZIP único",
            variable=self.download_type,
            value="zip",
            font=("Segoe UI", 9),
            fg="#e0e0e0",
            bg="#121316",
            selectcolor="#1f2127",
            activebackground="#121316",
            activeforeground="#00d26a"
        )
        opt_zip.pack(side="left")

        opt_folder = tk.Radiobutton(
            action_box,
            text="Extraer en carpeta directa",
            variable=self.download_type,
            value="folder",
            font=("Segoe UI", 9),
            fg="#e0e0e0",
            bg="#121316",
            selectcolor="#1f2127",
            activebackground="#121316",
            activeforeground="#00d26a"
        )
        opt_folder.pack(side="left", padx=(15, 0))

        self.btn_download = tk.Button(
            action_box,
            text="⬇️ DESCARGAR TODO AHORA",
            command=self.on_download_click,
            font=("Segoe UI", 11, "bold"),
            fg="#121316",
            bg="#00d26a",
            activebackground="#00b55b",
            activeforeground="#121316",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2"
        )
        self.btn_download.pack(side="right")

        # Console / Status Section
        console_lbl = tk.Label(
            main,
            text="ESTADO & REGISTRO:",
            font=("Segoe UI", 9, "bold"),
            fg="#9aa0a6",
            bg="#121316"
        )
        console_lbl.pack(anchor="w", pady=(0, 5))

        self.log_text = tk.Text(
            main,
            font=("Consolas", 9),
            bg="#0e0f11",
            fg="#c5c8cf",
            relief="flat",
            height=8,
            highlightthickness=1,
            highlightbackground="#24262c"
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        self.log("Bienvenido a UC Drive Downloader.")
        self.log("Pega el link y presiona 'Descargar Todo Ahora'.")

    def update_session_badge(self):
        if engine.is_profile_logged_in():
            self.badge_lbl.config(text="🟢 SESIÓN LISTA", bg="#103822", fg="#00ff88")
        else:
            self.badge_lbl.config(text="🟡 SESIÓN PENDIENTE", bg="#3d3013", fg="#ffcc00")

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"> {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.dest_folder.get())
        if folder:
            self.dest_folder.set(folder)

    def on_login_click(self):
        self.btn_login.config(state="disabled")
        self.log("Abriendo navegador para inicio de sesión seguro...")

        def _worker():
            try:
                asyncio.run(engine.run_login_flow(status_callback=self.log))
                self.after(0, self.update_session_badge)
            except Exception as e:
                self.log(f"Error en login: {str(e)}")
            finally:
                self.after(0, lambda: self.btn_login.config(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def on_download_click(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Atención", "Por favor pega un enlace de UC Drive.")
            return

        out_dir = self.dest_folder.get().strip()
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta de destino: {e}")
                return

        as_zip = (self.download_type.get() == "zip")

        self.btn_download.config(state="disabled", text="⏳ DESCARGANDO...")
        self.log(f"Iniciando tarea para: {url}")

        def _worker():
            try:
                result = asyncio.run(engine.download_uc_share(
                    url=url,
                    output_folder=out_dir,
                    as_zip=as_zip,
                    status_callback=self.log
                ))
                self.log(f"¡Completado con éxito!")
                self.after(0, lambda: messagebox.showinfo("Descarga Exitosa", f"Archivo listo en:\n{result}"))
            except Exception as e:
                err_msg = str(e)
                self.log(f"❌ Error: {err_msg}")
                self.after(0, lambda: messagebox.showerror("Error en Descarga", f"{err_msg}"))
            finally:
                self.after(0, lambda: self.btn_download.config(state="normal", text="⬇️ DESCARGAR TODO AHORA"))

        threading.Thread(target=_worker, daemon=True).start()

if __name__ == "__main__":
    app = UCDownloaderApp()
    app.mainloop()
