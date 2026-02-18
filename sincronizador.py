import os
import re
import unicodedata
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

MAPEO_ESTADOS = {
    "PENDIENTE FIRMA": "159",
    "PENDIENTE FIRMA PAPEL": "189",
    "PENDIENTE DE VALIDACION": "202",
    "VALIDADO": "202",
    "TRAMITE": "202",
    "CONTRATO": "161"
}

TEXTO_WOLF_POR_ID = {
    "159": "PENDIENTE FIRMA",
    "189": "PENDIENTE FIRMA MANUAL",
    "202": "VALIDADO",
    "161": "EN TRAMITE"
}

def normalizar(texto):
    if not texto: return ""
    texto = texto.upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def sincronizar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=400)
        context = browser.new_context(viewport={'width': 1366, 'height': 768})
        page_wolf = context.new_page()
        page_ignis = context.new_page()

        try:
            # --- LOGIN IGNIS ---
            print("🔑 Accediendo a Ignis...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            page_ignis.click("md-select[name='empresaLogin']")
            page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
            page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button:has-text('Entrar')")
            page_ignis.wait_for_timeout(3000)
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            page_ignis.wait_for_selector('input[placeholder="Cups..."]')

            # --- LOGIN WOLF ---
            print("🔑 Accediendo a Wolf CRM...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            url_filtros = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&Q_STATUS[]=159&Q_STATUS[]=189&Q_STATUS[]=202&Q_STATUS[]=161"
            page_wolf.goto(url_filtros)
            page_wolf.wait_for_selector("select#dt-length-0")
            page_wolf.select_option("select#dt-length-0", value="500")
            page_wolf.wait_for_timeout(4000)

            # --- PROCESO ---
            filas = page_wolf.locator("table.data-table tbody tr").all()
            print(f"📊 Analizando {len(filas)} filas...")

            for fila in filas:
                try:
                    texto_fila = fila.inner_text()
                    match_cups = re.search(r'ES00[A-Z0-9]{16,18}', texto_fila.upper())
                    if not match_cups: continue
                    cups = match_cups.group(0)
                    
                    estado_wolf_txt = "DESCONOCIDO"
                    for id_w, txt_w in TEXTO_WOLF_POR_ID.items():
                        if normalizar(txt_w) in normalizar(texto_fila):
                            estado_wolf_txt = txt_w
                            break

                    # --- BUSCAR EN IGNIS CON ESPERA DE CARGA ---
                    page_ignis.bring_to_front()
                    bus = page_ignis.locator('input[placeholder="Cups..."]:visible')
                    bus.click(click_count=3)
                    page_ignis.keyboard.press("Control+A")
                    page_ignis.keyboard.press("Backspace")
                    bus.fill(cups)
                    page_ignis.keyboard.press("Enter")
                    
                    # Clic en Aplicar Filtros
                    btn_aplicar = page_ignis.locator("button.aplicarFiltros")
                    if btn_aplicar.is_visible(): 
                        btn_aplicar.click()
                    
                    # 🔹 NUEVA ESPERA: Esperar a que el indicador de carga aparezca y desaparezca
                    # O simplemente esperar a que la fila contenga el CUPS actual
                    print(f"⏳ Esperando resultados para {cups}...")
                    
                    # Esperamos máximo 6 segundos a que la fila de la tabla contenga el CUPS que acabamos de escribir
                    try:
                        page_ignis.locator(".ui-grid-row").filter(has_text=cups).wait_for(state="visible", timeout=6000)
                    except:
                        pass # Si no aparece, el if de abajo lo gestionará como "No hallado"

                    fila_ignis = page_ignis.locator(".ui-grid-row").filter(has_text=cups).first
                    
                    if fila_ignis.is_visible():
                        texto_ignis = fila_ignis.inner_text()
                        nombre_estado_ignis = next((k for k in MAPEO_ESTADOS if normalizar(k) in normalizar(texto_ignis)), None)
                        
                        if nombre_estado_ignis:
                            id_objetivo = MAPEO_ESTADOS[nombre_estado_ignis]
                            texto_objetivo_wolf = TEXTO_WOLF_POR_ID[id_objetivo]

                            print(f"🔍 {cups}: Wolf({estado_wolf_txt}) | Ignis({nombre_estado_ignis})")

                            if normalizar(estado_wolf_txt) != normalizar(texto_objetivo_wolf):
                                print(f"📢 DISCORDANCIA en {cups}. Editando...")
                                page_wolf.bring_to_front()
                                
                                # Clic en lupa
                                lupa = fila.locator("span.edit-icon, i.fa-search-plus").first
                                lupa.scroll_into_view_if_needed()
                                lupa.evaluate("el => el.click()")

                                # Iframe
                                frame = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                                selector_status = frame.locator("select#EnergyContract__STATUS")
                                selector_status.wait_for(state="visible", timeout=10000)
                                
                                # Cambio y Guardado
                                selector_status.select_option(value=id_objetivo)
                                selector_status.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                                frame.locator("button#btn_save, button:has-text('Guardar')").first.click()
                                
                                page_wolf.wait_for_timeout(2000)
                                print(f"   ✅ Sincronizado.")
                            else:
                                print(f"👌 Ok.")
                    else:
                        print(f"❌ {cups} no hallado en Ignis (tras esperar carga).")

                except Exception as e:
                    print(f"⚠️ Error en {cups}: {e}")
                    page_wolf.keyboard.press("Escape")

        except Exception as e:
            traceback.print_exc()
        finally:
            print("\n🏁 Proceso terminado.")

if __name__ == "__main__":
    sincronizar()