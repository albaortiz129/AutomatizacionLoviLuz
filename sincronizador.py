import os
import re
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# MAPEO DE ESTADOS SEGÚN TUS GRUPOS
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
            # --- ROBOT IGNIS: LOGIN ---
            print("🌐 Robot Ignis: Iniciando sesión...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            page_ignis.click("md-select[name='empresaLogin']")
            page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
            page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button:has-text('Entrar')")
            page_ignis.wait_for_timeout(3000)
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            page_ignis.wait_for_selector("#inputBusquedaPaginacion")

            # --- ROBOT WOLF: EXTRACCIÓN ---
            print("🐺 Robot Wolf: Entrando en CRM...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/")
            page_wolf.wait_for_selector(".main-template-data-container-preloader", state="hidden")
            
            # Mostrar 500 registros
            print("📄 Expandiendo tabla Wolf...")
            page_wolf.select_option("#dt-length-0", value="500")
            page_wolf.wait_for_timeout(3000)

            # Aplicar filtros
            page_wolf.evaluate("document.querySelector('button.reportFormToggle2').click()")
            page_wolf.evaluate("""() => {
                const s = (id, vs) => {
                    const el = document.getElementById(id);
                    if(!el) return;
                    Array.from(el.options).forEach(o => o.selected = vs.includes(o.value));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    if(window.jQuery && window.jQuery(el).multiselect) window.jQuery(el).multiselect('refresh');
                };
                s('Q_COMERCIALIZADORA', ['IGNIS_ENERGIA']);
                s('Q_STATUS', ['159', '189', '202', '161']);
                generateReport('search', '');
            }""")
            
            page_wolf.wait_for_timeout(7000)
            cups_list = list(set(re.findall(r'ES00[A-Z0-9]{16,18}', page_wolf.content())))
            print(f"📊 {len(cups_list)} CUPS cargados.")

            # --- BUCLE DE BÚSQUEDA Y COMPARACIÓN ---
            for cups in cups_list:
                try:
                    print(f"\n Buscando: {cups}")
                    page_ignis.bring_to_front()
                    
                    # Limpiar buscador de forma agresiva
                    buscador = page_ignis.locator("#inputBusquedaPaginacion")
                    buscador.focus()
                    page_ignis.keyboard.press("Control+A")
                    page_ignis.keyboard.press("Backspace")
                    
                    # Escribir y buscar
                    page_ignis.keyboard.type(cups, delay=40)
                    page_ignis.keyboard.press("Enter")
                    page_ignis.wait_for_timeout(4000)

                    # Selector de fila de Ignis
                    fila = page_ignis.locator(f".ui-grid-row:has-text('{cups}')").first
                    if fila.is_visible():
                        texto_ignis = fila.inner_text().upper()
                        estado_ignis = next((k for k in MAPEO_ESTADOS if k in texto_ignis), None)
                        
                        if estado_ignis:
                            id_wolf_objetivo = MAPEO_ESTADOS[estado_ignis]
                            print(f"   📡 Ignis detectó: {estado_ignis} -> CRM ID: {id_wolf_objetivo}")

                            # Actualizar Wolf
                            page_edit = context.new_page()
                            page_edit.goto(f"https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/object.php?NAME={cups}")
                            
                            target = page_edit
                            for f in page_edit.frames:
                                if "object.php" in f.url: target = f; break
                            
                            target.wait_for_selector("#EnergyContract__STATUS")
                            actual_id = target.locator("#EnergyContract__STATUS").input_value()

                            if actual_id != id_wolf_objetivo:
                                print(f"   📢 ACTUALIZANDO: {actual_id} -> {id_wolf_objetivo}")
                                target.select_option("#EnergyContract__STATUS", value=id_wolf_objetivo)
                                # target.locator("#btn-save").click()
                            page_edit.close()
                    else:
                        print(f"   ❌ No hallado en Ignis.")

                except Exception:
                    continue

        except Exception as e:
            traceback.print_exc()
        finally:
            print("\n🏁 Proceso terminado.")

if __name__ == "__main__":
    sincronizar()