import os
import re
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# --- REGLAS DE NEGOCIO ---
MAPEO_ESTADOS = {
    "PENDIENTE FIRMA": "159",
    "PENDIENTE FIRMA PAPEL": "189",
    "PENDIENTE VALIDACION": "202",
    "VALIDADO": "202",
    "EN TRAMITE": "202",
    "CONTRATO": "161"
}

def sincronizar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=600)
        context = browser.new_context(viewport={'width': 1366, 'height': 768})

        page_wolf = context.new_page()
        page_ignis = context.new_page()

        try:
            # --- 1. LOGIN EN IGNIS (Fuerza navegación a contratos) ---
            print("🌐 Robot Ignis: Iniciando sesión...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            
            # Selección de empresa (según tu captura de pantalla)
            page_ignis.wait_for_selector("md-select[name='empresaLogin']")
            page_ignis.click("md-select[name='empresaLogin']")
            page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
            
            page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button:has-text('Entrar')")
            
            # ESPERA ACTIVA: Forzamos la entrada a contratos
            print("⏳ Ignis: Entrando en la sección de contratos...")
            page_ignis.wait_for_timeout(5000) # Tiempo para que Angular guarde el token de sesión
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            
            # Verificamos que el buscador esté cargado antes de seguir
            page_ignis.wait_for_selector("#inputBusquedaPaginacion", timeout=20000)
            print("✅ Robot Ignis: Sección de contratos cargada.")

            # --- 2. WOLFCRM: SALTO DIRECTO A FILTROS ---
            print("🐺 Wolf: Iniciando sesión y saltando a filtros...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            # Inyección directa por URL para saltar los multiselectores
            url_filtros = (
                "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?"
                "Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&"
                "Q_STATUS[]=159&Q_STATUS[]=189&Q_STATUS[]=202&Q_STATUS[]=161"
            )
            page_wolf.goto(url_filtros)
            page_wolf.wait_for_selector(".main-template-data-container-preloader", state="hidden")

            # Intentar poner 500 registros
            print("📄 Wolf: Expandiendo tabla...")
            try:
                page_wolf.wait_for_selector("select#dt-length-0", timeout=10000)
                page_wolf.select_option("select#dt-length-0", value="500")
                page_wolf.wait_for_timeout(5000)
            except:
                print("⚠️ No se pudo expandir a 500, se usará la vista actual.")

            # Extraer CUPS
            cups_list = list(set(re.findall(r'ES00[A-Z0-9]{16,18}', page_wolf.content())))
            print(f"📊 {len(cups_list)} CUPS listos para comparar.")

            # --- 3. COMPARACIÓN Y ACTUALIZACIÓN ---
            for cups in cups_list:
                try:
                    print(f"\n🔎 Procesando: {cups}")
                    page_ignis.bring_to_front()
                    
                    # Limpiar buscador de Ignis
                    bus = page_ignis.locator('input[placeholder="Cups..."]:visible')
                    bus.click(click_count=3)
                    page_ignis.keyboard.press("Control+A")
                    page_ignis.keyboard.press("Backspace")
                    bus.fill(cups)
                    page_ignis.keyboard.press("Enter")
                    
                    # Clic manual en la lupa/aplicar (según tu código anterior)
                    page_ignis.click("button.aplicarFiltros")
                    page_ignis.wait_for_timeout(4000)

                    # Buscar la fila del CUPS
                    fila = page_ignis.locator(".ui-grid-row").filter(has_text=cups).first
                    if fila.is_visible(timeout=3000):
                        texto_ignis = fila.inner_text().upper()
                        estado_detectado = next((k for k in MAPEO_ESTADOS if k in texto_ignis), None)
                        
                        if estado_detectado:
                            id_wolf = MAPEO_ESTADOS[estado_detectado]
                            print(f"   📡 Ignis: {estado_detectado} -> Wolf ID: {id_wolf}")

                            # Actualizar Wolf
                            page_edit = context.new_page()
                            page_edit.on("dialog", lambda d: d.accept())
                            page_edit.goto(f"https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/object.php?NAME={cups}")
                            
                            target = page_edit
                            for f in page_edit.frames:
                                if "object.php" in f.url: target = f; break
                            
                            target.wait_for_selector("#EnergyContract__STATUS", timeout=10000)
                            actual = target.locator("#EnergyContract__STATUS").input_value()

                            if actual != id_wolf:
                                print(f"   📢 CAMBIANDO: {actual} -> {id_wolf}")
                                target.select_option("#EnergyContract__STATUS", value=id_wolf)
                                # target.locator("#btn-save").click() # <-- Descomentar para guardar
                            page_edit.close()
                    else:
                        print(f"   ❌ No hallado en Ignis.")

                except Exception as e:
                    print(f"   ⚠️ Error con {cups}: {e}")

        except Exception as e:
            traceback.print_exc()
        finally:
            print("\n🏁 Tarea terminada.")

if __name__ == "__main__":
    sincronizar()