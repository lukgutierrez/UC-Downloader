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
        self.title("UC Drive Cloud Downloader v2.1 - Pro")
        self.geometry("840x720")
        self.minsize(780, 620)
        self.configure(bg="#121316")

        self.default_dest = os.path.join(os.path.expanduser("~"), "Downloads")
        self.dest_folder = tk.StringVar(value=self.default_dest)
        self.url_var = tk.StringVar(value="")
        self.download_type = tk.StringVar(value="folder")

        # Variables de estado
        self.discovered_files = []
        self.file_vars = []
        self.token_info = {}
        self.pwd_id = ""
        self.is_downloading = False
        self.cancel_requested = False

        self.setup_ui()
        self.update_session_badge()

    def setup_ui(self):
        # Header
        header = tk.Frame(self, bg="#1a1b1f", pady=12, padx=20)
        header.pack(fill="x")

        title_lbl = tk.Label(
            header,
            text="⚡ UC DRIVE CLOUD DOWNLOADER v2.1",
            font=("Segoe UI", 15, "bold"),
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
        main = tk.Frame(self, bg="#121316", padx=20, pady=10)
        main.pack(fill="both", expand=True)

        # Login Banner
        sess_frame = tk.Frame(main, bg="#1c1e24", padx=12, pady=8)
        sess_frame.pack(fill="x", pady=(0, 10))

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
            padx=10,
            pady=4,
            cursor="hand2"
        )
        self.btn_login.pack(side="right")

        # URL Input & Explorar Button
        url_lbl = tk.Label(
            main,
            text="ENLACE DE UC DRIVE (uc-share.com / drive.ucweb.com):",
            font=("Segoe UI", 9, "bold"),
            fg="#9aa0a6",
            bg="#121316"
        )
        url_lbl.pack(anchor="w", pady=(0, 4))

        url_box = tk.Frame(main, bg="#121316")
        url_box.pack(fill="x", pady=(0, 10))

        url_entry = tk.Entry(
            url_box,
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
        url_entry.pack(side="left", fill="x", expand=True, ipady=6)

        self.btn_explore = tk.Button(
            url_box,
            text="🔍 EXPLORAR LINK",
            command=self.on_explore_click,
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#2563eb",
            activebackground="#3b82f6",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2"
        )
        self.btn_explore.pack(side="right", padx=(8, 0))

        # Files Selection Tree Frame
        tree_header = tk.Frame(main, bg="#121316")
        tree_header.pack(fill="x", pady=(0, 4))

        self.lbl_tree_title = tk.Label(
            tree_header,
            text="ARCHIVOS & SUBCARPETAS DETECTADAS (Selecciona los que desees):",
            font=("Segoe UI", 9, "bold"),
            fg="#9aa0a6",
            bg="#121316"
        )
        self.lbl_tree_title.pack(side="left")

        btn_select_all = tk.Button(
            tree_header,
            text="Seleccionar Todos",
            command=self.select_all_files,
            font=("Segoe UI", 8),
            fg="#00d26a",
            bg="#1c1e24",
            activebackground="#26282f",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        btn_select_all.pack(side="right", padx=(4, 0))

        btn_deselect_all = tk.Button(
            tree_header,
            text="Deseleccionar Todos",
            command=self.deselect_all_files,
            font=("Segoe UI", 8),
            fg="#e0e0e0",
            bg="#1c1e24",
            activebackground="#26282f",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        btn_deselect_all.pack(side="right")

        # Scrollable Frame for Checkboxes
        tree_container = tk.Frame(main, bg="#1a1b1f", highlightthickness=1, highlightbackground="#2e313b", height=135)
        tree_container.pack(fill="x", pady=(0, 10))
        tree_container.pack_propagate(False)

        self.canvas = tk.Canvas(tree_container, bg="#18191d", highlightthickness=0)
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#18191d")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.lbl_empty = tk.Label(
            self.scrollable_frame,
            text="Pega un enlace arriba y presiona '🔍 EXPLORAR LINK' para ver videos y PDFs en subcarpetas.",
            font=("Segoe UI", 9, "italic"),
            fg="#6b7280",
            bg="#18191d",
            padx=10,
            pady=15
        )
        self.lbl_empty.pack(anchor="w")

        # Output Folder Section
        folder_lbl = tk.Label(
            main,
            text="CARPETA DE DESTINO:",
            font=("Segoe UI", 9, "bold"),
            fg="#9aa0a6",
            bg="#121316"
        )
        folder_lbl.pack(anchor="w", pady=(0, 4))

        folder_box = tk.Frame(main, bg="#121316")
        folder_box.pack(fill="x", pady=(0, 10))

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

        # Format Options & Download / Stop Buttons
        action_box = tk.Frame(main, bg="#121316")
        action_box.pack(fill="x", pady=(0, 10))

        opt_folder = tk.Radiobutton(
            action_box,
            text="Extraer en carpeta directa (Recomendado)",
            variable=self.download_type,
            value="folder",
            font=("Segoe UI", 9),
            fg="#e0e0e0",
            bg="#121316",
            selectcolor="#1f2127",
            activebackground="#121316",
            activeforeground="#00d26a"
        )
        opt_folder.pack(side="left")

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
        opt_zip.pack(side="left", padx=(15, 0))

        self.btn_download = tk.Button(
            action_box,
            text="⬇️ DESCARGAR SELECCIONADOS",
            command=self.on_download_click,
            font=("Segoe UI", 10, "bold"),
            fg="#121316",
            bg="#00d26a",
            activebackground="#00b55b",
            activeforeground="#121316",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2"
        )
        self.btn_download.pack(side="right")

        self.btn_stop = tk.Button(
            action_box,
            text="⏹️ DETENER",
            command=self.on_stop_click,
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#dc2626",
            activebackground="#ef4444",
            relief="flat",
            padx=12,
            pady=6,
            state="disabled",
            cursor="hand2"
        )
        self.btn_stop.pack(side="right", padx=(0, 8))

        # Progress Bars Section (Mejora 3: Visual Progress)
        prog_frame = tk.Frame(main, bg="#121316")
        prog_frame.pack(fill="x", pady=(0, 10))

        # Custom ttk style for green progress bar
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#1a1b1f",
            background="#00d26a",
            darkcolor="#00b55b",
            lightcolor="#00ff88",
            bordercolor="#2e313b"
        )

        prog_top_lbl = tk.Frame(prog_frame, bg="#121316")
        prog_top_lbl.pack(fill="x", pady=(0, 2))

        self.lbl_file_prog = tk.Label(
            prog_top_lbl,
            text="Progreso archivo actual: 0%",
            font=("Segoe UI", 8),
            fg="#9aa0a6",
            bg="#121316"
        )
        self.lbl_file_prog.pack(side="left")

        self.lbl_total_prog = tk.Label(
            prog_top_lbl,
            text="Progreso lote general: 0/0 archivos",
            font=("Segoe UI", 8, "bold"),
            fg="#00d26a",
            bg="#121316"
        )
        self.lbl_total_prog.pack(side="right")

        self.bar_file = ttk.Progressbar(prog_frame, style="Green.Horizontal.TProgressbar", orient="horizontal", mode="determinate")
        self.bar_file.pack(fill="x")

        # Console / Status Section
        console_lbl = tk.Label(
            main,
            text="ESTADO & REGISTRO:",
            font=("Segoe UI", 9, "bold"),
            fg="#9aa0a6",
            bg="#121316"
        )
        console_lbl.pack(anchor="w", pady=(0, 4))

        self.log_text = tk.Text(
            main,
            font=("Consolas", 9),
            bg="#0e0f11",
            fg="#c5c8cf",
            relief="flat",
            height=6,
            highlightthickness=1,
            highlightbackground="#24262c"
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        self.log("Bienvenido a UC Drive Cloud Downloader v2.1.")
        self.log("Pega el enlace arriba y presiona '🔍 EXPLORAR LINK'.")

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

    def select_all_files(self):
        for var in self.file_vars:
            var.set(True)

    def deselect_all_files(self):
        for var in self.file_vars:
            var.set(False)

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

    def on_explore_click(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Atención", "Por favor pega un enlace de UC Drive.")
            return

        self.btn_explore.config(state="disabled", text="🔍 EXPLORANDO...")
        self.log(f"Explorando enlace: {url}")

        def _worker():
            try:
                files, token_info, pwd_id = asyncio.run(engine.fetch_share_file_tree(url, status_callback=self.log))
                self.discovered_files = files
                self.token_info = token_info
                self.pwd_id = pwd_id

                self.after(0, self.render_file_tree)
                self.log(f"¡Exploración completa! Se encontraron {len(files)} archivo(s) en total.")
            except Exception as e:
                self.log(f"❌ Error al explorar: {str(e)}")
                self.after(0, lambda: messagebox.showerror("Error al explorar", str(e)))
            finally:
                self.after(0, lambda: self.btn_explore.config(state="normal", text="🔍 EXPLORAR LINK"))

        threading.Thread(target=_worker, daemon=True).start()

    def render_file_tree(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.file_vars.clear()

        if not self.discovered_files:
            lbl = tk.Label(
                self.scrollable_frame,
                text="No se encontraron archivos en este enlace.",
                font=("Segoe UI", 9, "italic"),
                fg="#ef4444",
                bg="#18191d",
                padx=10,
                pady=10
            )
            lbl.pack(anchor="w")
            return

        for idx, file_info in enumerate(self.discovered_files):
            var = tk.BooleanVar(value=True)
            self.file_vars.append(var)

            fname = file_info.get("file_name", f"archivo_{idx+1}")
            fsize = file_info.get("size", 0)
            fsize_mb = round(fsize / (1024 * 1024), 1)
            folder_tag = f"📁 [{file_info['folder_path']}] " if "folder_path" in file_info else ""

            cb = tk.Checkbutton(
                self.scrollable_frame,
                text=f"{folder_tag}{fname} ({fsize_mb} MB)",
                variable=var,
                font=("Segoe UI", 9),
                fg="#e0e0e0",
                bg="#18191d",
                selectcolor="#121316",
                activebackground="#18191d",
                activeforeground="#00d26a",
                padx=5,
                pady=2
            )
            cb.pack(anchor="w")

    def update_file_progress(self, pct):
        self.after(0, lambda: self._apply_file_prog(pct))

    def _apply_file_prog(self, pct):
        self.bar_file["value"] = pct
        self.lbl_file_prog.config(text=f"Progreso archivo actual: {pct}%")

    def update_total_progress(self, current, total):
        self.after(0, lambda: self._apply_total_prog(current, total))

    def _apply_total_prog(self, current, total):
        self.lbl_total_prog.config(text=f"Progreso lote general: {current}/{total} archivos")

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

        def _worker():
            self.is_downloading = True
            self.cancel_requested = False
            self.after(0, lambda: self.btn_download.config(state="disabled", text="⏳ DESCARGANDO..."))
            self.after(0, lambda: self.btn_stop.config(state="normal"))
            self.update_file_progress(0)

            try:
                files_to_download = []
                token_info = self.token_info
                pwd_id = self.pwd_id

                if not self.discovered_files:
                    self.log("Explorando enlace automáticamente...")
                    files, t_info, p_id = asyncio.run(engine.fetch_share_file_tree(url, status_callback=self.log))
                    self.discovered_files = files
                    token_info = t_info
                    pwd_id = p_id
                    self.after(0, self.render_file_tree)
                    files_to_download = files
                else:
                    for idx, var in enumerate(self.file_vars):
                        if var.get() and idx < len(self.discovered_files):
                            files_to_download.append(self.discovered_files[idx])

                if not files_to_download:
                    self.log("⚠️ No hay ningún archivo seleccionado para descargar.")
                    self.after(0, lambda: messagebox.showwarning("Atención", "Por favor selecciona al menos un archivo."))
                    return

                self.update_total_progress(0, len(files_to_download))

                result = asyncio.run(engine.download_selected_files(
                    selected_files=files_to_download,
                    token_info=token_info,
                    pwd_id=pwd_id,
                    output_folder=out_dir,
                    as_zip=as_zip,
                    status_callback=self.log,
                    file_progress_callback=self.update_file_progress,
                    total_progress_callback=self.update_total_progress,
                    cancel_check=lambda: self.cancel_requested
                ))

                if not self.cancel_requested:
                    self.log(f"¡Completado con éxito!")
                    self.update_file_progress(100)
                    self.after(0, lambda: messagebox.showinfo("Descarga Exitosa", f"Archivo(s) listos con su estructura en:\n{result}"))
            except Exception as e:
                err_msg = str(e)
                self.log(f"❌ {err_msg}")
                if not self.cancel_requested:
                    self.after(0, lambda: messagebox.showerror("Error en Descarga", f"{err_msg}"))
            finally:
                self.is_downloading = False
                self.after(0, lambda: self.btn_download.config(state="normal", text="⬇️ DESCARGAR SELECCIONADOS"))
                self.after(0, lambda: self.btn_stop.config(state="disabled"))

        threading.Thread(target=_worker, daemon=True).start()

    def on_stop_click(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.log("🛑 Solicitando detención de la descarga...")
            self.btn_stop.config(state="disabled")

if __name__ == "__main__":
    app = UCDownloaderApp()
    app.mainloop()
