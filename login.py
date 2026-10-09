import sys
import os
import asyncio
from playwright.async_api import async_playwright

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "profile")

async def login_window():
    os.makedirs(PROFILE_DIR, exist_ok=True)
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        print("Abriendo ventana de inicio de sesión de UC Drive...")
        await page.goto("https://drive.ucweb.com/", wait_until="networkidle")
        
        print("Por favor, inicia sesión en la ventana del navegador que se acaba de abrir.")
        print("Cuando hayas terminado de iniciar sesión, cerra la ventana del navegador.")
        
        # Wait until the user closes the page or browser
        while len(context.pages) > 0:
            await asyncio.sleep(1)
            
        await context.close()
        print("Sesión guardada exitosamente.")

if __name__ == "__main__":
    asyncio.run(login_window())
