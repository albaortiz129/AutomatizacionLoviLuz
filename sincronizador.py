import os
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN DE ESTADOS ---
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

        # --- APERTURA DE VENTANAS ---
        page_wolf = context.new_page()
        page_ignis = context.new_page()

        try:
            # --- LOGIN EN IGNIS + NAVEGACIÓN A CONTRATOS ---
            print("🌐 Robot Ignis: Iniciando sesión...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            
            # Selección de Empresa
            page_ignis.click("md-select[name='empresaLogin']")
            page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
            
            # Credenciales
            page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button[type='submit']:has-text('Entrar')")
            
            # ESPERA CRUCIAL: Esperar a que el login termine y forzar ir a Contratos
            print("🚀 Robot Ignis: Navegando a la sección de Contratos...")
            # Esperamos un poco a que el sistema procese el login antes de saltar de URL
            page_ignis.wait_for_timeout(3000) 
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            
            # Confirmar que el buscador de CUPS está ahí
            page_ignis.wait_for_selector("#inputBusquedaPaginacion", timeout=30000)
            print("✅ Robot Ignis: Sección de Contratos lista.")

            # --- LOGIN EN WOLFCRM ---
            print("🐺 Robot Wolf: Obteniendo lista...")
            page_wolf.bring_to_front()
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/")
            page_wolf.wait_for_selector(".main-template-data-container-preloader", state="hidden")
            
            # Aplicar filtros
            page_wolf.evaluate("document.querySelector('button.reportFormToggle2').click()")
            page_wolf.evaluate("""() => {
                const m = (id, vals) => {
                    const s = document.getElementById(id);
                    if(!s) return;
                    Array.from(s.options).forEach(o => o.selected = vals.includes(o.value));
                    s.dispatchEvent(new Event('change', { bubbles: true }));
                    if(window.jQuery && window.jQuery(s).multiselect) window.jQuery(s).multiselect('refresh');
                };
                m('Q_COMERCIALIZADORA', ['IGNIS_ENERGIA']);
                m('Q_STATUS', ['159', '189', '202', '161']);
                generateReport('search', '');
            }""")
            
            page_wolf.wait_for_timeout(8000)

            # Extraer CUPS
            cups_elements = page_wolf.locator("td a:has-text('ES00')").all_inner_texts()
            cups_list = list(set([c.strip() for c in cups_elements if c.strip().startswith("ES00")]))
            print(f"📊 {len(cups_list)} CUPS listos para comparar.")

            # --- COMPARACIÓN ---
            for cups in cups_list:
                try:
                    print(f"\n🔍 Buscando {cups} en Ignis...")
                    page_ignis.bring_to_front()
                    
                    # Asegurar que estamos en la URL correcta por si acaso
                    if "#/contratos" not in page_ignis.url:
                        page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
                        page_ignis.wait_for_selector("#inputBusquedaPaginacion")

                    bus = page_ignis.locator("#inputBusquedaPaginacion")
                    bus.click(click_count=3)
                    page_ignis.keyboard.press("Backspace")
                    page_ignis.keyboard.type(cups, delay=50)
                    page_ignis.keyboard.press("Enter")
                    page_ignis.wait_for_timeout(4000)

                    fila = page_ignis.locator(f".ui-grid-row:has-text('{cups}')").first
                    if fila.is_visible():
                        texto_ignis = fila.inner_text().upper()
                        estado_detectado = next((k for k in MAPEO_ESTADOS if k in texto_ignis), None)
                        
                        if estado_detectado:
                            id_objetivo = MAPEO_ESTADOS[estado_detectado]
                            print(f"   📡 Ignis: {estado_detectado} (ID: {id_objetivo})")

                            # Actualizar en Wolf (pestaña nueva)
                            page_edit = context.new_page()
                            page_edit.goto(f"https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/object.php?NAME={cups}")
                            page_edit.wait_for_load_state("networkidle")
                            
                            target = page_edit
                            for f in page_edit.frames:
                                if "object.php" in f.url: target = f; break
                            
                            target.wait_for_selector("#EnergyContract__STATUS")
                            actual_id = target.locator("#EnergyContract__STATUS").input_value()

                            if actual_id != id_objetivo:
                                print(f"   📢 CAMBIANDO: {actual_id} -> {id_objetivo}")
                                target.select_option("#EnergyContract__STATUS", value=id_objetivo)
                                # target.locator("#btn-save").click()
                            else:
                                print("   👌 Sin cambios.")
                            page_edit.close()
                    else:
                        print(f"   ❌ {cups} no encontrado.")

                except Exception as e:
                    print(f"   ⚠️ Error en CUPS {cups}: {e}")

        except Exception as e:
            traceback.print_exc()
        finally:
            print("\n🏁 Tarea finalizada.")
            browser.close()

if __name__ == "__main__":
    sincronizar()