import os
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

MAPEO_ESTADOS = {
    "PENDIENTE FIRMA": "159",
    "PENDIENTE FIRMA MANUAL": "189",
    "PENDIENTE FIRMA PAPEL": "189",
    "PENDIENTE VALIDACION": "194",
    "VERIFICADO": "194",
    "VALIDADO": "202",
    "EN TRAMITE": "161",
    "PUESTA EN MARCHA": "158",
    "ACTIVADO": "164"
}

def sincronizar_estados():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={'width': 1366, 'height': 768})
        page_wolf = context.new_page()

        try:
            # --- 1. LOGIN ---
            print("🐺 Entrando en WolfCRM...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            page_wolf.wait_for_load_state("networkidle")

            page_wolf.goto("https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/")
            
            print("⏳ Esperando carga...")
            page_wolf.wait_for_selector(".main-template-data-container-preloader", state="hidden")
            
            # Abrir panel de filtros
            page_wolf.evaluate("document.querySelector('button.reportFormToggle2').click()")
            page_wolf.wait_for_timeout(1500)

            # --- 2. FILTRADO + DISPARAR BÚSQUEDA (MÉTODO JS DIRECTO) ---
            print("🧠 Aplicando filtros y lanzando búsqueda...")
            
            page_wolf.evaluate("""() => {
                const marcarValores = (selectId, valores) => {
                    const select = document.getElementById(selectId);
                    if (!select) return;
                    Array.from(select.options).forEach(opt => opt.selected = false);
                    valores.forEach(v => {
                        const opt = Array.from(select.options).find(o => o.value === v);
                        if (opt) opt.selected = true;
                    });
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    if (window.jQuery && window.jQuery(select).multiselect) {
                        window.jQuery(select).multiselect('refresh');
                    }
                };

                // 1. Seleccionar Ignis
                marcarValores('Q_COMERCIALIZADORA', ['IGNIS_ENERGIA']);
                
                // 2. Seleccionar Estados
                marcarValores('Q_STATUS', ['159', '189', '202', '161']);

                // 3. EJECUTAR LA FUNCIÓN DE BÚSQUEDA DE WOLF DIRECTAMENTE
                // Invocamos la función que tiene el botón en el onclick
                if (typeof generateReport === 'function') {
                    console.log('Ejecutando generateReport...');
                    generateReport('search', '');
                } else {
                    // Si la función no está accesible, forzamos clic en el botón
                    document.querySelector('.reportFormSearchButton').click();
                }
            }""")

            # Espera generosa para que la tabla se recargue
            print("🚀 Búsqueda lanzada. Esperando resultados...")
            page_wolf.wait_for_timeout(7000)

            # --- 3. EXTRACCIÓN DE CUPS ---
            # Aseguramos que la tabla tenga datos antes de seguir
            page_wolf.wait_for_selector("table.reportTable", timeout=15000)
            
            cups_elements = page_wolf.locator("table.reportTable td a:has-text('ES00')").all_inner_texts()
            cups_limpios = list(set([c.strip() for c in cups_elements if c.strip().startswith("ES00")]))
            print(f"📊 {len(cups_limpios)} contratos detectados en Wolf.")

            if not cups_limpios:
                print("📭 No se encontraron resultados. ¿Se ha aplicado bien el filtro?")
                return

            # --- 4. PORTAL IGNIS ---
            page_ignis = context.new_page()
            print("🌐 Entrando en Portal Ignis...")
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            page_ignis.fill("input[type='text']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[type='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button:has-text('Entrar')")
            page_ignis.wait_for_load_state("networkidle")

            # --- 5. BUCLE ---
            for cups in cups_limpios:
                try:
                    print(f"\n🔍 Comprobando: {cups}")
                    page_ignis.bring_to_front()
                    
                    bus = page_ignis.wait_for_selector("#inputBusquedaPaginacion")
                    bus.click(click_count=3)
                    page_ignis.keyboard.press("Backspace")
                    bus.fill(cups)
                    page_ignis.keyboard.press("Enter")
                    page_ignis.wait_for_timeout(3500)

                    selector_fila = f"//div[contains(@class, 'ui-grid-row')][descendant::a[contains(text(), '{cups}')]]"
                    
                    if page_ignis.locator(selector_fila).count() > 0:
                        est_ignis = page_ignis.locator(selector_fila).locator("strong.ng-binding").first.inner_text().upper().strip()
                        print(f"📡 Ignis: {est_ignis}")

                        id_wolf_nuevo = MAPEO_ESTADOS.get(est_ignis)
                        if id_wolf_nuevo:
                            page_wolf.bring_to_front()
                            page_wolf.goto(f"https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/object.php?NAME={cups}")
                            
                            # Gestión de frame para actualización
                            target = page_wolf
                            page_wolf.wait_for_load_state("domcontentloaded")
                            for frame in page_wolf.frames:
                                if "object.php" in frame.url:
                                    target = frame; break
                            
                            target.wait_for_selector("#EnergyContract__STATUS", timeout=10000)
                            id_actual = target.locator("#EnergyContract__STATUS").input_value()

                            if id_actual != id_wolf_nuevo:
                                print(f"📢 CAMBIANDO: {id_actual} -> {id_wolf_nuevo}")
                                target.select_option("#EnergyContract__STATUS", value=id_wolf_nuevo)
                                # target.locator("#btn-save").click() 
                                print(f"✅ Sincronizado.")
                            else:
                                print(f"👌 Ya estaba correcto.")
                    else:
                        print(f"❌ No aparece en Ignis.")

                except Exception as e:
                    print(f"⚠️ Error procesando {cups}")

        except Exception as e:
            print(f"🚨 ERROR CRÍTICO: {e}")
            traceback.print_exc()
        finally:
            print("\n🏁 Proceso terminado.")
            page_wolf.wait_for_timeout(10000)
            browser.close()

if __name__ == "__main__":
    sincronizar_estados()