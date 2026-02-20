import os
import re
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

def limpiar_nombre_producto(texto):
    """Limpia el nombre del producto de Wolf para que coincida con Ignis."""
    if not texto or "Seleccione" in texto or "..." in texto:
        return None
    
    limpio = texto.upper()
    limpio = limpio.replace("!", "").replace("(", "").replace(")", "")
    # Corta antes de "2.0TD..." o similares para facilitar la búsqueda
    limpio = re.split(r'\d+\.\d+TD', limpio)[0] 
    return limpio.strip()

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
        
        # Usamos las páginas del contexto para evitar pestañas fantasma
        page_wolf = context.pages[0]
        page_ignis = context.new_page()

        try:
            # --- 1. LOGIN IGNIS ---
            print("🔹 Accediendo a Ignis...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login", wait_until="networkidle")
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

            url_filtro = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&Q_STATUS[]=158"
            page_wolf.goto(url_filtro)
            page_wolf.wait_for_selector("table.data-table")

            # Bucle principal
            for i in range(500): 
                try:
                    page_wolf.bring_to_front()
                    filas_locator = page_wolf.locator("table.data-table tbody tr")
                    if i >= filas_locator.count(): break
                    
                    fila = filas_locator.nth(i)
                    fila.scroll_into_view_if_needed()
                    
                    if "No data available" in fila.inner_text(): break

                    fila.locator("span.edit-icon, i.fa-search-plus").first.click()
                    page_wolf.wait_for_selector("#wolfWindowInFrameFrame", timeout=10000)
                    frame_wolf = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                    
                    # --- EXTRACCIÓN ---
                    page_wolf.wait_for_timeout(1000) 
                    cups_valor = frame_wolf.locator("#EnergyContract__NAME").input_value().strip()
                    dni_valor = frame_wolf.locator("#EnergyContract__DNI_FIRMANTE").input_value().strip()
                    
                    producto_full = frame_wolf.locator("#EnergyContract__MODALIDAD_PRODUCTO").evaluate(
                        "sel => sel.options[sel.selectedIndex].text"
                    )

                    print(f"🔎 Capturado: {cups_valor} | Producto: {producto_full}")

                    if not cups_valor:
                        page_wolf.keyboard.press("Escape")
                        continue

                    # --- 3. PROCESO EN IGNIS ---
                    page_ignis.bring_to_front()
                    
                    # Navegar a Alta Contrato
                    page_ignis.locator("md-list-item, a").filter(has_text=re.compile(r"Alta contrato", re.I)).first.click()
                    
                    page_ignis.wait_for_selector("input[name='Cups']", timeout=10000)
                    
                    # Rellenar y Buscar
                    page_ignis.fill("input[name='Cups']", cups_valor)
                    page_ignis.fill("input[name='Identificador']", dni_valor)
                    page_ignis.locator("button:has-text('BUSCAR')").first.click()
                    
                    # Esperar mensaje y aceptar
                    page_ignis.wait_for_timeout(2000)
                    btn_ok = page_ignis.locator("button:has-text('Aceptar'), button:has-text('ACEPTAR')").first
                    if btn_ok.is_visible(): 
                        btn_ok.click()
                        page_ignis.wait_for_timeout(1500)

                    # --- SELECCIÓN BUSCANDO POR TEXTO EN IGNIS ---
                    nombre_limpio = limpiar_nombre_producto(producto_full)
                    if nombre_limpio:
                        try:
                            # 1. Clic en el desplegable de Producto
                            dropdown = page_ignis.locator("md-select[name='GrupoTarifa']").first
                            dropdown.click()
                            page_ignis.wait_for_timeout(800)
                            
                            # 2. ESCRIBIR el nombre para filtrar (Ignis suele permitir escribir directamente 
                            # cuando el foco está en el select o tiene un input de búsqueda interno)
                            print(f"⌨️ Escribiendo producto: {nombre_limpio}")
                            page_ignis.keyboard.type(nombre_limpio, delay=100)
                            page_ignis.wait_for_timeout(1000)
                            
                            # 3. Buscar la opción que contenga el texto y clicarla
                            opcion = page_ignis.locator(f"md-option:has-text('{nombre_limpio}')").first
                            if opcion.is_visible():
                                opcion.click()
                                print(f"✅ Seleccionado: {nombre_limpio}")
                            else:
                                # Si no se ve, intentamos con un Enter por si el filtro dejó solo una opción
                                page_ignis.keyboard.press("Enter")
                                print(f"⚠️ Opción no visible, se intentó con Enter")
                                
                        except Exception as e:
                            print(f"⚠️ Error al buscar producto: {e}")
                            page_ignis.keyboard.press("Escape")

                    input("👉 Revisa Ignis y pulsa ENTER para el siguiente...")
                    
                    # Volver a Wolf y cerrar ficha
                    page_wolf.bring_to_front()
                    page_wolf.keyboard.press("Escape")
                    page_wolf.wait_for_timeout(500)

                except Exception as e:
                    print(f"❌ Error en registro {i}: {e}")
                    try: page_wolf.keyboard.press("Escape")
                    except: pass

        except Exception:
            print(traceback.format_exc())

if __name__ == "__main__":
    ejecutar_consulta_ignis()