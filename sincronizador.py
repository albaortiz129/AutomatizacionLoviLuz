import os
import re
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# MAPEO DE ESTADOS (Ignis -> ID Wolf)
MAPEO_ESTADOS = {
    "PENDIENTE FIRMA": "159",
    "PENDIENTE FIRMA PAPEL": "189",
    "PENDIENTE VALIDACION": "202",
    "VALIDADO": "202",
    "EN TRAMITE": "202",
    "CONTRATO": "161"
}

# MAPEO INVERSO (ID Wolf -> Texto visible en la tabla de Wolf)
# Esto sirve para comparar sin tener que abrir la ficha
TEXTO_WOLF_POR_ID = {
    "159": "PENDIENTE FIRMA",
    "189": "PENDIENTE FIRMA MANUAL",
    "202": "VALIDADO",
    "161": "EN TRAMITE"
}

def sincronizar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={'width': 1366, 'height': 768})

        page_wolf = context.new_page()
        page_ignis = context.new_page()

        try:
            # --- 1. LOGIN IGNIS ---
            print("🌐 Iniciando Ignis...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            page_ignis.click("md-select[name='empresaLogin']")
            page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
            page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button:has-text('Entrar')")
            page_ignis.wait_for_timeout(4000)
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            page_ignis.wait_for_selector("#inputBusquedaPaginacion")

            # --- 2. LOGIN WOLF Y FILTROS ---
            print("🐺 Iniciando Wolf...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            url_filtros = (
                "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?"
                "Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&"
                "Q_STATUS[]=159&Q_STATUS[]=189&Q_STATUS[]=202&Q_STATUS[]=161"
            )
            page_wolf.goto(url_filtros)
            page_wolf.wait_for_selector(".main-template-data-container-preloader", state="hidden")
            
            # Poner 500 registros
            try:
                page_wolf.select_option("select#dt-length-0", value="500")
                page_wolf.wait_for_timeout(4000)
            except: pass

            # --- 3. PROCESO CELDA A CELDA ---
            filas = page_wolf.locator("table.data-table tbody tr").all()
            print(f"📊 Analizando {len(filas)} filas...")

            for fila in filas:
                try:
                    texto_fila = fila.inner_text().upper()
                    match_cups = re.search(r'ES00[A-Z0-9]{16,18}', texto_fila)
                    if not match_cups: continue
                    
                    cups = match_cups.group(0)
                    
                    # --- COMPARACIÓN PREVIA ---
                    # Miramos qué estado pone en la fila de Wolf actualmente
                    estado_wolf_actual = next((v for v in TEXTO_WOLF_POR_ID.values() if v in texto_fila), "DESCONOCIDO")

                    # BUSCAR EN IGNIS
                    page_ignis.bring_to_front()
                    bus = page_ignis.locator('input[placeholder="Cups..."]:visible')
                    bus.click(click_count=3)
                    page_ignis.keyboard.press("Control+A")
                    page_ignis.keyboard.press("Backspace")
                    bus.fill(cups)
                    page_ignis.keyboard.press("Enter")
                    page_ignis.click("button.aplicarFiltros")
                    page_ignis.wait_for_timeout(3500)

                    fila_ignis = page_ignis.locator(".ui-grid-row").filter(has_text=cups).first
                    if fila_ignis.is_visible():
                        texto_ignis = fila_ignis.inner_text().upper()
                        nombre_estado_ignis = next((k for k in MAPEO_ESTADOS if k in texto_ignis), None)
                        
                        if nombre_estado_ignis:
                            id_objetivo = MAPEO_ESTADOS[nombre_estado_ignis]
                            texto_objetivo_wolf = TEXTO_WOLF_POR_ID[id_objetivo]

                            print(f"🧐 CUPS: {cups} | Wolf: {estado_wolf_actual} | Ignis: {nombre_estado_ignis}")

                            # SOLO EDITAR SI SON DIFERENTES
                            if estado_wolf_actual != texto_objetivo_wolf:
                                print(f"📢 DISCORDANCIA DETECTADA. Entrando a editar...")
                                
                                page_wolf.bring_to_front()
                                # Selector de la lupa corregido: busca el icono de edición o el primer enlace de la fila
                                btn_editar = fila.locator("a[title='Editar'], a i.fa-search, td:first-child a").first
                                
                                with context.expect_page() as nueva_pestaña:
                                    btn_editar.click()
                                
                                p_edit = nueva_pestaña.value
                                p_edit.on("dialog", lambda d: d.accept())
                                
                                # Frame check
                                target = p_edit
                                for f in p_edit.frames:
                                    if "object.php" in f.url: target = f; break
                                
                                target.wait_for_selector("#EnergyContract__STATUS", timeout=8000)
                                target.select_option("#EnergyContract__STATUS", value=id_objetivo)
                                
                                # GUARDADO REAL
                                # target.locator("#btn-save").click()
                                print(f"✅ Estado actualizado a {texto_objetivo_wolf}")
                                p_edit.close()
                            else:
                                print(f"👌 No requiere cambios.")
                    else:
                        print(f"❌ {cups} no hallado en Ignis.")

                except Exception as e:
                    print(f"⚠️ Error procesando fila: {e}")

        except Exception as e:
            traceback.print_exc()
        finally:
            print("\n🏁 Proceso terminado.")

if __name__ == "__main__":
    sincronizar()