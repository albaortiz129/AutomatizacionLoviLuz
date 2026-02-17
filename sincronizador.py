import os
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# --- REGLAS DE COMPARACIÓN ---
# IGNIS -> WOLFCRM
MAPEO_ESTADOS = {
    "PENDIENTE FIRMA": "159",           # 1- PENDIENTE FIRMA
    "PENDIENTE FIRMA PAPEL": "189",     # 2- PENDIENTE FIRMA MANUAL
    "PENDIENTE VALIDACION": "202",      # 3- VALIDADO (Grupo A)
    "VALIDADO": "202",                  # 3- VALIDADO (Grupo B)
    "EN TRAMITE": "202",                # 3- VALIDADO (Grupo C)
    "CONTRATO": "161"                   # 4- EN TRAMITE
}

def sincronizar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={'width': 1366, 'height': 768})
        page = context.new_page()

        try:
            # --- 1. LOGIN Y FILTRADO EN WOLFCRM ---
            print("🐺 WolfCRM: Iniciando sesión...")
            page.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page.click('input[type="submit"]')
            
            page.goto("https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/")
            page.wait_for_selector(".main-template-data-container-preloader", state="hidden", timeout=30000)
            
            print("🔍 Aplicando filtros de búsqueda...")
            page.click("button.reportFormToggle2") # Abre el panel de filtros
            
            page.evaluate("""() => {
                const setVal = (id, values) => {
                    const el = document.getElementById(id);
                    if(!el) return;
                    Array.from(el.options).forEach(o => o.selected = values.includes(o.value));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    if(window.jQuery && window.jQuery(el).multiselect) window.jQuery(el).multiselect('refresh');
                };
                setVal('Q_COMERCIALIZADORA', ['IGNIS_ENERGIA']);
                setVal('Q_STATUS', ['159', '189', '202', '161']);
                generateReport('search', '');
            }""")
            
            print("⏳ Esperando resultados del CRM...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(7000) # Tiempo vital para que la tabla se dibuje

            # Extraemos los CUPS (Buscamos enlaces que contengan ES00)
            cups_elements = page.locator("a:has-text('ES00')").all_inner_texts()
            cups_limpios = list(set([c.strip() for c in cups_elements if c.strip().startswith("ES00")]))
            
            if not cups_limpios:
                print("❌ No se encontraron CUPS en la tabla de Wolf. Revisa los filtros.")
                return
            
            print(f"✅ Se han encontrado {len(cups_limpios)} CUPS para procesar.")

            # --- 2. LOGIN EN IGNIS ---
            print("\n🌐 Ignis: Iniciando sesión...")
            page.goto("https://agentes.ignisluz.es/#/login")
            page.wait_for_selector("input[type='text']")
            page.fill("input[type='text']", os.getenv("IGNIS_USER") or "")
            page.fill("input[type='password']", os.getenv("IGNIS_PASS") or "")
            page.click("button:has-text('Entrar')")
            page.wait_for_url("**/contratos**", timeout=20000)

            # --- 3. BUCLE DE COMPARACIÓN CUPS POR CUPS ---
            for cups in cups_limpios:
                try:
                    print(f"\n🔎 [CUPS: {cups}]")
                    
                    # Buscar en Ignis
                    page.goto("https://agentes.ignisluz.es/#/contratos")
                    bus = page.wait_for_selector("#inputBusquedaPaginacion")
                    bus.click(click_count=3)
                    page.keyboard.press("Backspace")
                    page.keyboard.type(cups, delay=50) # Tecleo humano para activar Angular
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(4000)

                    # Leer estado en la fila de Ignis
                    fila = page.locator(f".ui-grid-row:has-text('{cups}')").first
                    if not fila.is_visible():
                        print(f"   ❌ No encontrado en Ignis.")
                        continue

                    texto_fila = fila.inner_text().upper()
                    estado_ignis_detectado = None
                    for nombre_estado, id_wolf in MAPEO_ESTADOS.items():
                        if nombre_estado in texto_fila:
                            estado_ignis_detectado = nombre_estado
                            id_objetivo_wolf = id_wolf
                            break

                    if estado_ignis_detectado:
                        print(f"   📡 Ignis dice: {estado_ignis_detectado}")
                        
                        # Ir al contrato en Wolf para comparar
                        page.goto(f"https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/object.php?NAME={cups}")
                        page.wait_for_load_state("domcontentloaded")
                        
                        # Manejo del frame de Wolf
                        target = page
                        for f in page.frames:
                            if "object.php" in f.url: target = f; break
                        
                        target.wait_for_selector("#EnergyContract__STATUS")
                        estado_actual_wolf = target.locator("#EnergyContract__STATUS").input_value()

                        if estado_actual_wolf != id_objetivo_wolf:
                            print(f"   ⚠️ DESVIACIÓN: Wolf ({estado_actual_wolf}) != Ignis ({id_objetivo_wolf})")
                            target.select_option("#EnergyContract__STATUS", value=id_objetivo_wolf)
                            # target.locator("#btn-save").click() # <-- Descomentar para guardar cambios
                            print(f"   ✅ Sincronizado correctamente.")
                        else:
                            print(f"   👌 Ya están sincronizados.")
                    else:
                        print(f"   ⚠️ Estado en Ignis no reconocido.")

                except Exception as e:
                    print(f"   ❗ Error procesando este CUPS: {e}")

        except Exception as e:
            traceback.print_exc()
        finally:
            print("\n🏁 Proceso terminado.")
            page.wait_for_timeout(5000)
            browser.close()

if __name__ == "__main__":
    sincronizar()