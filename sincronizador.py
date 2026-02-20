import os
import re
import unicodedata
import traceback
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN DE ESTADOS ACTUALIZADA (SEGÚN SELECTOR WOLF CRM) ---
MAPEO_ESTADOS = {
    "SIN ENVIAR": "214",
    "PENDIENTE FIRMA": "215",
    "PENDIENTE FIRMA PAPEL": "216",
    "PENDIENTE VALIDACION": "217",
    "PENDIENTE DE SOLICITAR ATR": "218",
    "TRAMITE": "219",
    "REVISION INTERNA": "220",
    "CONTRATO": "221",
    "BAJA": "222",
    "BAJA POR MODIFICACION": "223",
    "CADUCADO FIRMA": "224",
    "INCIDENCIA": "225",
    "EXPIRADO": "226",
    "DISTRIBUIDORA": "227",
    "RECHAZADO": "228",
    "KO": "229",
    # Renovaciones 
    "SIN ENVIAR RENOVACION": "230",
    "PENDIENTE FIRMA RENOVACION": "231",
    "PENDIENTE FIRMA PAPEL RENOVACION": "232",
    "CADUCADO RENOVACION": "233",
    "VALIDAR RENOVACION": "234",
    "INCIDENCIA RENOVACION": "235",
    "REVISION INTERNA RENOVACION": "236",
    "RENOVACION ACEPTADA": "237",
    "RENOVACION RECHAZADA": "238",
    "CONTRATO MOTIVO: RENOVACION": "239",
    "RENOVACION: ACEPTADA TACITA": "240",
    "CONTRATO MOTIVO: RENOVACION TACITA": "241",
    # Compatibilidad para lectura
    "PENDIENTE FIRMA MANUAL": "189",
    "PENDIENTE DE VALIDACION": "202",
    "VALIDADO": "202"
}

def escribir_log(mensaje, tipo="INFO"):
    carpeta_logs = "LOGS"
    if not os.path.exists(carpeta_logs):
        os.makedirs(carpeta_logs)
    
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    timestamp = ahora.strftime("%Y-%m-%d %H:%M:%S")
    
    iconos = {
        "INFO": "🔹",
        "OK": "✅",
        "ADVERTENCIA": "⚠️",
        "ERROR": "❌",
        "SISTEMA": "⚙️"
    }
    
    icono = iconos.get(tipo, "🔹")
    nombre_archivo = os.path.join(carpeta_logs, f"registro_{fecha_hoy}.txt")
    linea = f"[{timestamp}] {icono} {mensaje}"
    
    print(linea)
    with open(nombre_archivo, "a", encoding="utf-8") as f:
        f.write(linea + "\n")

def normalizar(texto):
    if not texto: return ""
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = texto.upper().replace("IGNIS ", "").strip()
    texto = re.sub(r'\s+', ' ', texto)
    return texto

def calcular_vencimiento(fecha_str):
    try:
        fecha_str = re.search(r'\d{2}/\d{2}/\d{4}', fecha_str).group(0)
        fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        fecha_vencimiento = fecha_dt.replace(year=fecha_dt.year + 1)
        return fecha_vencimiento.strftime("%d/%m/%Y")
    except: return None

def sincronizar():
    with sync_playwright() as p:
        ruta_sesion = os.path.join(os.getcwd(), "SesionIgnis")
        
        context = p.chromium.launch_persistent_context(
            ruta_sesion,
            headless=False,
            slow_mo=150,
            viewport={'width': 1366, 'height': 768},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page_wolf = context.new_page()
        page_ignis = context.new_page()

        escribir_log("="*60, "SISTEMA")
        escribir_log("EMPEZANDO A REVISAR CONTRATOS", "SISTEMA")
        escribir_log("="*60, "SISTEMA")

        try:
            escribir_log("Entrando en Ignis Energía...", "INFO")
            page_ignis.goto("https://agentes.ignisluz.es/#/login", wait_until="networkidle")
            
            if "login" in page_ignis.url:
                try:
                    page_ignis.wait_for_selector("md-select[name='empresaLogin']", state="visible", timeout=10000)
                    page_ignis.click("md-select[name='empresaLogin']")
                    page_ignis.wait_for_selector("md-option:has-text('LOOP ELECTRICIDAD Y GAS')", state="visible")
                    page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
                    
                    campo_user = page_ignis.locator("input[name='usuario']")
                    campo_user.click(click_count=3)
                    page_ignis.keyboard.press("Backspace")
                    campo_user.fill(os.getenv("IGNIS_USER") or "")
                    
                    campo_pass = page_ignis.locator("input[name='password']")
                    campo_pass.click(click_count=3)
                    page_ignis.keyboard.press("Backspace")
                    campo_pass.fill(os.getenv("IGNIS_PASS") or "")
                    
                    page_ignis.wait_for_timeout(1000)
                    
                    boton_entrar = page_ignis.locator("button:has-text('Entrar')")
                    if boton_entrar.is_enabled():
                        boton_entrar.click()
                    else:
                        page_ignis.keyboard.press("Enter")
                except Exception as e:
                    escribir_log(f"Error en login o ya logueado: {str(e)}", "INFO")
            
            page_ignis.wait_for_timeout(4000)
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            
            escribir_log("Entrando en Wolf CRM...", "INFO")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            escribir_log("Buscando contratos en Wolf...", "INFO")
            url_wolf = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&Q_STATUS[]=159&Q_STATUS[]=189&Q_STATUS[]=202"
            
            page_wolf.goto(url_wolf)
            page_wolf.wait_for_selector("select#dt-length-0")
            page_wolf.select_option("select#dt-length-0", value="500")
            page_wolf.wait_for_timeout(4000)

            filas_wolf = page_wolf.locator("table.data-table tbody tr").all()
            escribir_log(f"Tengo {len(filas_wolf)} contratos para mirar hoy.", "SISTEMA")

            contador_cups = 0
            page_ignis.bring_to_front()
            page_ignis.wait_for_selector(".ui-grid-render-container-body", state="visible")
            page_ignis.wait_for_timeout(5000) 

            for fila in filas_wolf:
                try:
                    texto_fila_crudo = fila.inner_text()
                    if not texto_fila_crudo.strip() or "No se encontraron" in texto_fila_crudo: break

                    contador_cups += 1
                    if contador_cups % 50 == 0:
                        escribir_log(f"Llevo {contador_cups} contratos. Limpiando memoria de Ignis...", "SISTEMA")
                        page_ignis.bring_to_front()
                        page_ignis.reload()
                        page_ignis.wait_for_timeout(5000)

                    cups = "S/N"
                    # --- CAMBIO AQUÍ: Detectar si el texto REAL de la celda tiene IGNIS ---
                    celdas_wolf = fila.locator("td").all()
                    estado_anterior_wolf = "EN TRAMITE"
                    ya_es_estado_nuevo = False 

                    for celda in celdas_wolf:
                        texto_celda_real = celda.inner_text().upper()
                        txt_normalizado = normalizar(texto_celda_real)
                        
                        for k in MAPEO_ESTADOS:
                            if txt_normalizado == normalizar(k):
                                estado_anterior_wolf = k
                                if "IGNIS" in texto_celda_real: # Si la celda contiene IGNIS, ya está actualizado
                                    ya_es_estado_nuevo = True
                                break
                        if estado_anterior_wolf != "EN TRAMITE": break

                    match_cups = re.search(r'ES00[A-Z0-9]{16,18}', normalizar(texto_fila_crudo))
                    if not match_cups: continue
                    cups = match_cups.group(0)
                    
                    page_ignis.bring_to_front()
                    encontrado_en_ignis = False
                    for intento in range(1, 4):
                        if intento > 1:
                            escribir_log(f"CUPS {cups}: No aparece, reintentando (Intento {intento})...", "INFO")
                            page_ignis.wait_for_timeout(3000)

                        page_ignis.evaluate("document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = 0")
                        page_ignis.wait_for_timeout(600)

                        encontrado_input = False
                        for d in [0, 800, 1600, 2400, 3200]:
                            page_ignis.evaluate(f"document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = {d}")
                            page_ignis.wait_for_timeout(300)
                            input_cups = page_ignis.locator('input[placeholder="Cups..."]')
                            if input_cups.count() > 0 and input_cups.is_visible():
                                input_cups.click(click_count=3)
                                page_ignis.keyboard.press("Backspace")
                                input_cups.fill(cups)
                                page_ignis.keyboard.press("Enter")
                                encontrado_input = True
                                break
                        
                        if encontrado_input:
                            page_ignis.locator("button.aplicarFiltros").first.click()
                            fila_target = page_ignis.locator(f".ui-grid-row:has-text('{cups}')").first
                            try:
                                fila_target.wait_for(state="visible", timeout=8000)
                                encontrado_en_ignis = True
                                break 
                            except: continue

                    if not encontrado_en_ignis:
                        continue

                    celdas_ignis = fila_target.locator(".ui-grid-cell").all()
                    estado_en_ignis = "OTRO"
                    for celda in celdas_ignis:
                        txt_i = normalizar(celda.inner_text())
                        for k in MAPEO_ESTADOS:
                            if txt_i == normalizar(k):
                                estado_en_ignis = k
                                break
                        if estado_en_ignis != "OTRO": break

                    id_ignis = MAPEO_ESTADOS.get(estado_en_ignis)

                    # --- LÓGICA DE ACTUALIZACIÓN ---
                    # Actualizamos si el nombre es distinto O si el estado en Wolf no tiene el prefijo "IGNIS"
                    debe_actualizar = (estado_en_ignis != estado_anterior_wolf) or (not ya_es_estado_nuevo)

                    if not debe_actualizar and estado_en_ignis != "CONTRATO":
                        escribir_log(f"CUPS {cups} | Wolf: {estado_anterior_wolf} | Ignis: {estado_en_ignis} | Sin cambios.", "INFO")
                        continue

                    if estado_en_ignis == "OTRO":
                        continue

                    # (Lógica de fechas para CONTRATO...)
                    fecha_alta_ignis = None
                    if estado_en_ignis == "CONTRATO":
                        for d in range(0, 5000, 800):
                            page_ignis.evaluate(f"document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = {d}")
                            page_ignis.wait_for_timeout(300)
                            columna = page_ignis.locator(".ui-grid-header-cell").filter(has_text=re.compile(r"F\. Alta|Fecha Alta", re.I)).first
                            if columna.count() > 0:
                                idx = columna.evaluate("el => Array.from(el.parentNode.children).indexOf(el)")
                                fecha_alta_ignis = fila_target.locator(".ui-grid-cell").nth(idx).inner_text().strip()
                                if re.search(r'\d{2}/\d{2}/\d{4}', fecha_alta_ignis): break

                    page_wolf.bring_to_front()
                    fila.locator("span.edit-icon, i.fa-search-plus").first.click()

                    frame = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                    selector_status = frame.locator("select#EnergyContract__STATUS")
                    selector_status.wait_for(state="visible", timeout=12000)
                    
                    selector_status.select_option(value=id_ignis)
                    selector_status.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")

                    venc = ""
                    if estado_en_ignis == "CONTRATO" and fecha_alta_ignis:
                        venc = calcular_vencimiento(fecha_alta_ignis)
                        frame.locator("#EnergyContract__START_DATE").fill(fecha_alta_ignis)
                        if venc: 
                            frame.locator("#EnergyContract__DUE_DATE").fill(venc)
                    
                    frame.locator(".save-object-btn").first.click()
                    page_wolf.locator("#wolfWindowInFrame").wait_for(state="hidden", timeout=12000)
                    
                    page_wolf.reload()
                    page_wolf.wait_for_timeout(3000)
                    
                    # Log original
                    fila_nueva = page_wolf.locator(f"tr:has-text('{cups}')").first
                    estado_confirmado_wolf = "DESCONOCIDO"
                    if fila_nueva.count() > 0:
                        celdas_nuevas = fila_nueva.locator("td").all()
                        for celda_n in celdas_nuevas:
                            txt_n = normalizar(celda_n.inner_text())
                            if txt_n in MAPEO_ESTADOS:
                                estado_confirmado_wolf = txt_n
                                break

                    prefijo = "IGNIS " if estado_confirmado_wolf != "CONTRATO" else ""
                    detalles_registro = f"CUPS {cups} | Wolf Anterior: {estado_anterior_wolf} | Ignis: {estado_en_ignis} | Wolf Actual: {prefijo}{estado_confirmado_wolf}"
                    if estado_en_ignis == "CONTRATO" and fecha_alta_ignis:
                         detalles_registro += f" | F. Alta: {fecha_alta_ignis} | Venc: {venc}"

                    escribir_log(detalles_registro, "OK")
                    page_ignis.wait_for_timeout(4000)

                except Exception as e:
                    try: page_wolf.keyboard.press("Escape")
                    except: pass

        except Exception:
            escribir_log("¡ERROR GORDO! El programa se ha parado.", "ERROR")
            print(traceback.format_exc())
        finally:
            escribir_log("="*60, "SISTEMA")
            escribir_log("COMPROBACIÓN FINALIZADA")
            escribir_log("="*60, "SISTEMA")
            context.close()

if __name__ == "__main__":
    sincronizar()