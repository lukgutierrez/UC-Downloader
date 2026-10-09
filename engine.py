import os
import sys
import asyncio
import zipfile
import shutil
import time
import urllib.request
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(BASE_DIR, "profile")
TEMP_DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_downloads")

def is_profile_logged_in():
    cookies_path = os.path.join(PROFILE_DIR, "Default", "Network", "Cookies")
    simple_cookies = os.path.join(PROFILE_DIR, "Default", "Cookies")
    return os.path.exists(cookies_path) or os.path.exists(simple_cookies) or os.path.exists(PROFILE_DIR)

async def run_login_flow(status_callback=None):
    os.makedirs(PROFILE_DIR, exist_ok=True)
    if status_callback:
        status_callback("Abriendo navegador para iniciar sesión...")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://drive.ucweb.com/", wait_until="networkidle")

        if status_callback:
            status_callback("Iniciá sesión en el navegador abierto. Cierra la ventana cuando termines.")

        while len(context.pages) > 0:
            await asyncio.sleep(1)

        await context.close()
        if status_callback:
            status_callback("Sesión guardada con éxito.")

def download_file_direct(url, dest_path, progress_callback=None, cancel_check=None):
    """Descarga un archivo con urllib en streaming reportando progreso real."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    )
    with urllib.request.urlopen(req) as response, open(dest_path, "wb") as out_file:
        total_size = int(response.info().get("Content-Length", 0))
        chunk_size = 1024 * 512  # 512 KB
        downloaded = 0
        last_report = time.time()

        while True:
            if cancel_check and cancel_check():
                raise Exception("Descarga cancelada por el usuario.")
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)

            now = time.time()
            if now - last_report >= 0.8 or downloaded == total_size:
                last_report = now
                if progress_callback and total_size > 0:
                    percent = int((downloaded / total_size) * 100)
                    dl_mb = round(downloaded / (1024 * 1024), 1)
                    tot_mb = round(total_size / (1024 * 1024), 1)
                    progress_callback(percent, dl_mb, tot_mb)

async def download_uc_share(url, output_folder, as_zip=True, status_callback=None, progress_callback=None):
    os.makedirs(PROFILE_DIR, exist_ok=True)
    os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

    for f in os.listdir(TEMP_DOWNLOAD_DIR):
        fp = os.path.join(TEMP_DOWNLOAD_DIR, f)
        try:
            if os.path.isfile(fp):
                os.remove(fp)
            elif os.path.isdir(fp):
                shutil.rmtree(fp)
        except Exception:
            pass

    if status_callback:
        status_callback("Iniciando conexión con UC Drive...")

    if not url.startswith("http"):
        url = "https://" + url

    downloaded_files = []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()

        share_files = []
        token_info = {}
        pwd_id = url.split("?")[0].rstrip("/").split("/")[-1]

        async def on_response(res):
            nonlocal token_info
            if "sharepage/v2/detail" in res.url:
                try:
                    data = await res.json()
                    t_info = data.get("data", {}).get("token_info", {})
                    if t_info:
                        token_info = t_info
                    detail_info = data.get("data", {}).get("detail_info", {})
                    items = detail_info.get("list", [])
                    if items:
                        for it in items:
                            if not any(x.get("fid") == it.get("fid") for x in share_files):
                                share_files.append(it)
                except Exception:
                    pass
            elif "sharepage/detail" in res.url:
                try:
                    data = await res.json()
                    items = data.get("data", {}).get("list", [])
                    if items:
                        for it in items:
                            if not any(x.get("fid") == it.get("fid") for x in share_files):
                                share_files.append(it)
                except Exception:
                    pass

        page.on("response", on_response)

        if status_callback:
            status_callback("Cargando enlace compartido...")

        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2500)

        # Si el enlace contiene carpetas, abrirlas usando el texto exacto de la carpeta
        if any(f.get("dir") for f in share_files) or (len(share_files) == 1 and share_files[0].get("dir")):
            folder_item = next((f for f in share_files if f.get("dir")), None)
            folder_name = folder_item.get("file_name") if folder_item else None
            
            # Limpiar la lista previa para quedarnos con los archivos reales de adentro
            share_files.clear()
            
            if folder_name:
                folder_loc = page.get_by_text(folder_name).last
                if await folder_loc.count() > 0:
                    if status_callback:
                        status_callback(f"Abriendo carpeta: {folder_name}...")
                    await folder_loc.click()
                    await page.wait_for_timeout(3000)

        total_detected = len(share_files)
        if total_detected == 0:
            await context.close()
            raise Exception("No se detectaron archivos en el enlace. Verificá que el enlace sea válido y tu sesión esté activa.")

        stoken = token_info.get("stoken", "")

        if status_callback:
            status_callback(f"¡Se detectaron {total_detected} archivo(s)! Iniciando descarga automática por lotes rotativos...")

        headers = {
            "referer": "https://drive.ucweb.com/",
            "content-type": "application/json",
            "x-u-req-res-encoding": "no"
        }

        # Procesar cada archivo 1 a 1 de forma 100% limpia por API
        for idx, file_info in enumerate(share_files):
            fname = file_info.get("file_name", f"archivo_{idx+1}")
            fsize = file_info.get("size", 0)
            fid = file_info.get("fid")
            fid_token = file_info.get("share_fid_token", "")
            pdir_fid = file_info.get("pdir_fid", "0")
            fsize_mb = round(fsize / (1024 * 1024), 1)

            if status_callback:
                status_callback(f"[{idx+1}/{total_detected}] Procesando: {fname} ({fsize_mb} MB)...")

            # 1. Guardar mediante llamada directa a la API de UC
            save_payload = {
                "stoken": stoken,
                "pwd_id": pwd_id,
                "fid_list": [fid],
                "fid_token_list": [fid_token] if fid_token else [],
                "pdir_fid": pdir_fid,
                "to_pdir_fid": "0"
            }

            save_res = await context.request.post(
                "https://m-intldrive.ucweb.com/1/clouddrive/share/sharepage/save?ve=&fve=1.8.8&pr=UCBrowser&fr=pc&cc=&sys=win32&ut=&ch=&pc=",
                headers=headers,
                data=save_payload
            )
            save_data = await save_res.json()
            task_id = save_data.get("data", {}).get("task_id")

            # Esperar a que la tarea de guardado finalice y nos devuelva el nuevo FID
            saved_fid = None
            if task_id:
                for _ in range(20):
                    await asyncio.sleep(0.5)
                    task_res = await context.request.get(
                        f"https://m-intldrive.ucweb.com/1/clouddrive/task?ve=&fve=1.8.8&pr=UCBrowser&fr=pc&cc=&sys=win32&ut=&ch=&pc=&task_id={task_id}&retry_index=0",
                        headers=headers
                    )
                    task_data = await task_res.json()
                    t_info = task_data.get("data", {})
                    if t_info.get("status") == 2:  # Completado
                        save_as = t_info.get("save_as", {})
                        top_fids = save_as.get("save_as_download_top_fids") or save_as.get("save_as_top_fids")
                        if top_fids:
                            saved_fid = top_fids[0]
                        break

            # Si no vino por task, buscarlo en el listado del root de la nube
            if not saved_fid:
                sort_res = await context.request.get(
                    "https://m-intldrive.ucweb.com/1/clouddrive/file/sort?ve=&fve=1.8.8&pr=UCBrowser&fr=pc&cc=&sys=win32&ut=&ch=&pc=&pdir_fid=0&_page=1&_size=20&_fetch_total=false&_fetch_sub_dirs=1&_sort=&recent_file_size=0",
                    headers={"referer": "https://drive.ucweb.com/", "x-u-req-res-encoding": "no"}
                )
                sort_data = await sort_res.json()
                for it in sort_data.get("data", {}).get("list", []):
                    if not it.get("dir"):
                        base_candidate = os.path.splitext(fname)[0]
                        if base_candidate[:15] in it.get("file_name", ""):
                            saved_fid = it.get("fid")
                            break

            if not saved_fid:
                if status_callback:
                    status_callback(f"⚠️ Aviso: No se pudo guardar {fname}, saltando...")
                continue

            # 2. Solicitar enlace directo de descarga
            if status_callback:
                status_callback(f"[{idx+1}/{total_detected}] Generando enlace de descarga directa...")

            dl_res = await context.request.post(
                "https://m-intldrive.ucweb.com/1/clouddrive/file/download?ve=&fve=1.8.8&pr=UCBrowser&fr=pc&cc=&sys=win32&ut=&ch=&pc=",
                headers=headers,
                data={"fids": [saved_fid]}
            )
            dl_json = await dl_res.json()
            dl_list = dl_json.get("data", [])
            if not dl_list or not dl_list[0].get("download_url"):
                if status_callback:
                    status_callback(f"⚠️ Error obteniendo link de {fname}, saltando...")
                continue

            download_url = dl_list[0]["download_url"]
            dest_file_path = os.path.join(TEMP_DOWNLOAD_DIR, fname)

            # 3. Descargar el archivo directamente a la PC con progreso en tiempo real
            if status_callback:
                status_callback(f"[{idx+1}/{total_detected}] Descargando a tu PC...")

            def _on_prog(pct, cur_mb, tot_mb):
                if status_callback:
                    status_callback(f"⬇️ {fname}: {pct}% ({cur_mb} MB / {tot_mb} MB)")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                download_file_direct,
                download_url,
                dest_file_path,
                _on_prog,
                None
            )

            downloaded_files.append(dest_file_path)
            if status_callback:
                status_callback(f"✅ Descargado: {fname}")

            # 4. Borrar inmediatamente de la nube de UC para liberar espacio
            if status_callback:
                status_callback(f"[{idx+1}/{total_detected}] Liberando espacio en la nube...")

            await context.request.post(
                "https://m-intldrive.ucweb.com/1/clouddrive/file/delete?ve=&fve=1.8.8&pr=UCBrowser&fr=pc&cc=&sys=win32&ut=&ch=&pc=",
                headers=headers,
                data={"filelist": [saved_fid]}
            )
            await asyncio.sleep(0.5)

        await context.close()

    if not downloaded_files:
        raise Exception("No se descargó ningún archivo. Verificá los permisos del enlace.")

    if status_callback:
        status_callback("Organizando los archivos finales...")

    final_name = f"UC_Descarga_{int(time.time())}"
    if as_zip:
        zip_output_path = os.path.join(output_folder, f"{final_name}.zip")
        if status_callback:
            status_callback(f"Empaquetando en ZIP: {os.path.basename(zip_output_path)}...")

        with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in downloaded_files:
                if os.path.isfile(file_path):
                    zipf.write(file_path, os.path.basename(file_path))

        if status_callback:
            status_callback(f"🎉 ¡COMPLETADO! Archivo ZIP listo en: {zip_output_path}")
        return zip_output_path
    else:
        out_target = os.path.join(output_folder, final_name)
        os.makedirs(out_target, exist_ok=True)
        for file_path in downloaded_files:
            shutil.move(file_path, os.path.join(out_target, os.path.basename(file_path)))
        if status_callback:
            status_callback(f"🎉 ¡COMPLETADO! Archivos listos en: {out_target}")
        return out_target
