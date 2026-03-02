import os
import re
import unicodedata
import traceback
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN DE ESTADOS ACTUALIZADA SEGÚN TU TABLA (IDs WOLF CRM) ---
MAPEO_ESTADOS = {
    "SIN ENVIAR": "214",           # IGNIS SIN ENVIAR
    "PENDIENTE FIRMA": "215",      # IGNIS PENDIENTE FIRMA
    "PENDIENTE FIRMA PAPEL": "216",# IGNIS PENDIENTE FIRMA PAPEL
    "PENDIENTE VALIDACION": "217", # IGNIS PENDIENTE VALIDACION
    "PENDIENTE DE VALIDACION": "217", 
    "PENDIENTE DE SOLICITAR ATR": "218", # IGNIS PENDIENTE DE SOLICITAR ATR
    "TRAMITE": "219",              # IGNIS TRAMITE
    "REVISION INTERNA": "220",     # IGNIS REVISION INTERNA
    "CONTRATO": "221",             # ACTIVADO
    "BAJA": "222",                 # IGNIS BAJA
    "BAJA POR MODIFICACION": "223",# IGNIS BAJA POR MODIFICACION
    "CADUCADO FIRMA": "224",       # IGNIS CADUCADO FIRMA
    "INCIDENCIA": "225",           # IGNIS INCIDENCIA
    "EXPIRADO": "226",             # IGNIS EXPIRADO
    "DISTRIBUIDORA": "227",        # IGNIS DISTRIBUIDORA
    "RECHAZADO": "228",            # IGNIS RECHAZADO
    "KO": "229",                   # IGNIS KO
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
    # Aseguramos que "PENDIENTE DE VALIDACION" se compare igual que "PENDIENTE VALIDACION"
    texto = texto.replace("DE ", "")
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
            # --- 1. LOGIN IGNIS ---
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
            
            # --- 2. LOGIN WOLF ---
            escribir_log("Entrando en Wolf CRM...", "INFO")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            escribir_log("Buscando contratos en Wolf con los nuevos filtros...", "INFO")
            
            # IDs del 214 al 229 + los antiguos para limpieza
            estados_ids = [214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 189, 202]
            query_status = "&".join([f"Q_STATUS[]={i}" for i in estados_ids])
            url_wolf = f"https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&{query_status}"
            
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
                    celdas_wolf = fila.locator("td").all()
                    texto_crm_real = "DESCONOCIDO"

                    for celda in celdas_wolf:
                        t = celda.inner_text().upper()
                        if any(normalizar(k) == normalizar(t) for k in MAPEO_ESTADOS):
                            texto_crm_real = t
                            break

                    match_cups = re.search(r'ES00[A-Z0-9]{16,18}', normalizar(texto_fila_crudo))
                    if not match_cups: continue
                    cups = match_cups.group(0)
                    
                    page_ignis.bring_to_front()
                    encontrado = False
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
                                page_ignis.locator("button.aplicarFiltros").first.click()
                                page_ignis.wait_for_timeout(4000)
                                encontrado_input = True
                                break
                        
                        if encontrado_input:
                            fila_target = page_ignis.locator(f".ui-grid-row:has-text('{cups}')").first
                            try:
                                fila_target.wait_for(state="visible", timeout=8000)
                                encontrado = True
                                break 
                            except: continue

                    if not encontrado:
                        continue

                    # Identificar estado en Ignis con scroll total
                    estado_ignis = "OTRO"
                    for d in [0, 800, 1600, 2400, 3200]:
                        page_ignis.evaluate(f"document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = {d}")
                        page_ignis.wait_for_timeout(300)
                        celdas_i = fila_target.locator(".ui-grid-cell").all()
                        for c in celdas_i:
                            txt_norm = normalizar(c.inner_text())
                            if txt_norm in [normalizar(k) for k in MAPEO_ESTADOS]:
                                estado_ignis = txt_norm; break
                        if estado_ignis != "OTRO": break

                    # LÓGICA DE ACTUALIZACIÓN MEJORADA
                    if estado_ignis != "OTRO":
                        norm_ignis = normalizar(estado_ignis)
                        norm_wolf = normalizar(texto_crm_real)
                        
                        falta_prefijo = "IGNIS" not in texto_crm_real.upper() and "ACTIVADO" not in texto_crm_real.upper()
                        son_distintos = norm_ignis != norm_wolf

                        if falta_prefijo or son_distintos:
                            page_wolf.bring_to_front()
                            fila.locator("span.edit-icon, i.fa-search-plus").first.click()
                            frame = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                            sel = frame.locator("select#EnergyContract__STATUS")
                            sel.wait_for(state="visible", timeout=12000)
                            
                            # Buscar la clave original para obtener el ID
                            id_objetivo = next(MAPEO_ESTADOS[k] for k in MAPEO_ESTADOS if normalizar(k) == norm_ignis)
                            sel.select_option(value=id_objetivo)
                            sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")

                            fecha_alta_ignis = None
                            if norm_ignis == normalizar("CONTRATO"):
                                page_ignis.bring_to_front()
                                page_ignis.evaluate("document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = 2000")
                                col = page_ignis.locator(".ui-grid-header-cell").filter(has_text=re.compile(r"F\. Alta", re.I)).first
                                if col.count() > 0:
                                    idx = col.evaluate("el => Array.from(el.parentNode.children).indexOf(el)")
                                    fecha_alta_ignis = fila_target.locator(".ui-grid-cell").nth(idx).inner_text().strip()
                                    page_wolf.bring_to_front()
                                    frame.locator("#EnergyContract__START_DATE").fill(fecha_alta_ignis)
                                    venc = calcular_vencimiento(fecha_alta_ignis)
                                    if venc: frame.locator("#EnergyContract__DUE_DATE").fill(venc)

                            frame.locator(".save-object-btn").first.click()
                            page_wolf.locator("#wolfWindowInFrame").wait_for(state="hidden", timeout=12000)
                            page_wolf.reload(); page_wolf.wait_for_timeout(2000)
                            
                            # LOG DETALLADO
                            prefijo = "IGNIS " if norm_ignis != normalizar("CONTRATO") else ""
                            escribir_log(f"CUPS {cups} | Wolf Anterior: {texto_crm_real} | Ignis: {estado_ignis} | Wolf Actual: {prefijo}{estado_ignis}", "OK")
                        else:
                            escribir_log(f"CUPS {cups} | Wolf: {texto_crm_real} | Ignis: {estado_ignis} | Resultado: Sin cambios necesarios.", "INFO")

                except Exception:
                    try: page_wolf.keyboard.press("Escape")
                    except: pass
        finally:
            escribir_log("="*60, "SISTEMA")
            escribir_log("COMPROBACIÓN FINALIZADA", "SISTEMA")
            escribir_log("="*60, "SISTEMA")
            context.close()

if __name__ == "__main__":
    sincronizar()