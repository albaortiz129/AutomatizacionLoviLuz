import os
import re
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

def ejecutar_consulta_ignis():
    with sync_playwright() as p:
        ruta_sesion = os.path.join(os.getcwd(), "SesionIgnis")
        
        context = p.chromium.launch_persistent_context(
            ruta_sesion,
            headless=False,
            slow_mo=200, 
            viewport={'width': 1366, 'height': 768},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page_wolf = context.new_page()
        page_ignis = context.new_page()

        try:
            # --- 1. LOGIN IGNIS ---
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            if "login" in page_ignis.url:
                try:
                    page_ignis.wait_for_selector("input[name='usuario']", timeout=5000)
                    page_ignis.click("md-select[name='empresaLogin']")
                    page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
                    page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
                    page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
                    page_ignis.click("button:has-text('Entrar')")
                    page_ignis.wait_for_timeout(3000)
                except: pass

            # --- 2. LOGIN WOLF ---
            print("🔹 Accediendo a Wolf CRM...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            
            if page_wolf.locator("#userLogin").is_visible():
                page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
                page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
                page_wolf.click('input[type="submit"]')

            # Filtro: IGNIS + Estado 158
            url_filtro = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&Q_STATUS[]=158"
            page_wolf.goto(url_filtro)
            page_wolf.wait_for_selector("table.data-table", timeout=12000)

            filas = page_wolf.locator("table.data-table tbody tr").all()
            print(f"✅ Se han encontrado {len(filas)} contratos.")

            for fila in filas:
                try:
                    if "No data available" in fila.inner_text(): break

                    # 1. Abrir la lupa en Wolf
                    fila.locator("span.edit-icon, i.fa-search-plus").first.click()
                    page_wolf.wait_for_selector("#wolfWindowInFrameFrame", timeout=10000)
                    frame_wolf = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                    
                    # 2. CAPTURA DE DATOS
                    input_cups_wolf = frame_wolf.locator("#EnergyContract__NAME")
                    input_dni_wolf = frame_wolf.locator("#EnergyContract__DNI_FIRMANTE")
                    input_cups_wolf.wait_for(state="visible", timeout=8000)
                    
                    cups_valor = input_cups_wolf.input_value()
                    dni_valor = input_dni_wolf.input_value()

                    if not cups_valor or not dni_valor:
                        page_wolf.keyboard.press("Escape")
                        continue

                    # --- 3. NAVEGACIÓN Y LLENADO EN IGNIS ---
                    page_ignis.bring_to_front()
                    
                    # MEJORA: Hacemos clic en el menú lateral en lugar de ir por URL directa
                    # El selector busca el botón "Alta contrato" en la lista del menú
                    btn_alta = page_ignis.locator("md-list-item:has-text('Alta contrato'), a:has-text('Alta contrato')").first
                    btn_alta.click()
                    
                    # Esperar a que los campos de la imagen aparezcan
                    page_ignis.wait_for_selector("input[name='Cups']", state="visible", timeout=10000)
                    
                    # Rellenar CUPS
                    page_ignis.fill("input[name='Cups']", cups_valor)
                    page_ignis.keyboard.press("Enter")
                    page_ignis.wait_for_timeout(1000)
                    
                    # Rellenar Identificador
                    page_ignis.fill("input[name='Identificador']", dni_valor)
                    page_ignis.keyboard.press("Tab")

                    # Hacer clic en el botón BUSCAR que sale en tu imagen
                    # Usamos .first porque a veces hay buscadores ocultos en el DOM
                    page_ignis.locator("button:has-text('BUSCAR')").first.click()
                    
                    print(f"📍 Procesado en Ignis: {cups_valor} | {dni_valor}")
                    
                    # PAUSA DE CONTROL
                    input("👉 Revisa Ignis. Presiona ENTER en la consola para ir al siguiente...")

                    # Volver a Wolf y cerrar popup
                    page_wolf.bring_to_front()
                    page_wolf.keyboard.press("Escape")
                    page_wolf.wait_for_timeout(800)

                except Exception as e:
                    print(f"⚠️ Error en registro: {e}")
                    page_wolf.bring_to_front()
                    page_wolf.keyboard.press("Escape")
                    continue

        except Exception:
            print(traceback.format_exc())
        
        print("\n🏁 Proceso finalizado.")

if __name__ == "__main__":
    ejecutar_consulta_ignis()