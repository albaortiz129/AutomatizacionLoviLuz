import os
import re
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

def ejecutar_consulta_ignis():
    with sync_playwright() as p:
        # Usamos la carpeta de sesión persistente
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
            # --- 1. LOGIN IGNIS (Solo si es necesario) ---
            print("🔹 Verificando acceso a Ignis...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            try:
                page_ignis.wait_for_selector("input[name='usuario']", timeout=4000)
                page_ignis.click("md-select[name='empresaLogin']")
                page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
                page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
                page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
                page_ignis.click("button:has-text('Entrar')")
                page_ignis.wait_for_timeout(2000)
            except:
                print("✅ Sesión activa en Ignis.")

            # --- 2. LOGIN WOLF Y FILTRO ---
            print("🔹 Accediendo a Wolf CRM...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            
            if page_wolf.locator("#userLogin").is_visible():
                page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
                page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
                page_wolf.click('input[type="submit"]')

            # Filtro: Pendiente revisar documentación (158)
            url_filtro = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_STATUS[]=158"
            page_wolf.goto(url_filtro)
            page_wolf.wait_for_selector("table.data-table", timeout=10000)

            filas = page_wolf.locator("table.data-table tbody tr").all()
            print(f"✅ Hay {len(filas)} contratos para consultar.")

            for fila in filas:
                try:
                    # 1. Pillamos el CUPS del texto de la fila
                    texto_fila = fila.inner_text()
                    match_cups = re.search(r'ES00[A-Z0-9]{16,18}', texto_fila)
                    if not match_cups: continue
                    cups_valor = match_cups.group(0)

                    # 2. Le damos a la lupa para ver los datos (DNI)
                    fila.locator("span.edit-icon, i.fa-search-plus").first.click()
                    
                    # 3. Extraemos el DNI del frame sin tocar nada
                    frame_wolf = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                    input_dni_wolf = frame_wolf.locator("input[id*='IDENTIFIER']").first
                    input_dni_wolf.wait_for(state="visible", timeout=8000)
                    dni_valor = input_dni_wolf.input_value()

                    print(f"🔎 Info capturada: CUPS {cups_valor} | DNI {dni_valor}")

                    # 4. Ir a Ignis - Alta Rápida y BUSCAR
                    page_ignis.bring_to_front()
                    page_ignis.goto("https://agentes.ignisluz.es/#/contrato/alta-rapida")
                    
                    page_ignis.wait_for_selector("input[name='Cups']", state="visible")
                    
                    # Rellenamos campos de búsqueda
                    page_ignis.fill("input[name='Cups']", cups_valor)
                    page_ignis.keyboard.press("Enter")
                    page_ignis.fill("input[name='Identificador']", dni_valor)
                    page_ignis.keyboard.press("Tab")

                    # Clic en BUSCAR
                    btn_buscar = page_ignis.locator("button.buscarCups")
                    btn_buscar.click()
                    
                    print(f"🚀 Consulta realizada para {cups_valor}. Esperando 6 segundos para ver resultado...")
                    # Dejamos tiempo para que TÚ veas el resultado en pantalla
                    page_ignis.wait_for_timeout(6000) 

                    # 5. Volver a Wolf y cerrar la ventana de la lupa para la siguiente fila
                    page_wolf.bring_to_front()
                    page_wolf.keyboard.press("Escape")
                    page_wolf.wait_for_timeout(1000)

                except Exception as e:
                    print(f"⚠️ Error consultando fila: {e}")
                    try: page_wolf.keyboard.press("Escape")
                    except: pass
                    continue

        except Exception:
            print(traceback.format_exc())
        finally:
            print("⚙️ Proceso de consulta terminado.")
            context.close()

if __name__ == "__main__":
    ejecutar_consulta_ignis()