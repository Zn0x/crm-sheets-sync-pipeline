import os
import sys
from datetime import datetime
import gspread
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuración de Endpoints y Credenciales de API ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.crm-partner-platform.com")
API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID", "default_org")

# --- Configuración de Google Sheets ---
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE", "credentials.json")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "CRM_Agencies_Database")
DESTINATION_SHEET_INDEX = int(os.getenv("DESTINATION_SHEET_INDEX", "0"))
AUDIT_LOGS_SHEET = os.getenv("AUDIT_LOGS_SHEET", "Execution_Logs")
PIPELINE_NAME = os.getenv("PIPELINE_NAME", "CRM_Agencies_ETL_Pipeline")


def log_execution_timestamp(status="SUCCESS"):
    """Registra la trazabilidad de la corrida en la pestaña de auditoría."""
    if not os.path.exists(GOOGLE_CREDS_FILE):
        print("[WARN] Archivo de credenciales no encontrado. Auditoría remota omitida.")
        return

    try:
        gc = gspread.service_account(filename=GOOGLE_CREDS_FILE)
        sh_control = gc.open(AUDIT_LOGS_SHEET)
        worksheet_logs = sh_control.get_worksheet(0)

        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M:%S")

        row_data = [PIPELINE_NAME, date_str, time_str, status]
        col_a_vals = worksheet_logs.col_values(1)
        next_row = len(col_a_vals) + 1
        target_range = f"A{next_row}:D{next_row}"

        worksheet_logs.update(range_name=target_range, values=[row_data])
        print(f"[INFO] Auditoría de ejecución registrada: {status}")
    except Exception as err:
        print(f"[WARN] Error al persistir log de auditoría: {err}")


def authenticate_api():
    """Autentica contra la API REST externa y extrae el token Bearer/Auth."""
    if not API_USERNAME or not API_PASSWORD:
        raise ValueError("Credenciales de API (API_USERNAME / API_PASSWORD) no definidas.")

    auth_endpoint = f"{API_BASE_URL}/resources/authentication/authenticate"
    payload = {
        "username": API_USERNAME,
        "password": API_PASSWORD,
        "micrositeId": ORGANIZATION_ID,
    }

    print(f"[INFO] Autenticando contra endpoint de CRM...")
    response = requests.post(auth_endpoint, json=payload, timeout=30)
    response.raise_for_status()

    token = response.json().get("token")
    if not token:
        raise RuntimeError("La API no retornó un token de sesión válido.")

    print("[INFO] Token de sesión adquirido exitosamente.")
    return token


def fetch_all_agencies(token):
    """Consume de forma recursiva/iterativa los registros paginados del endpoint REST."""
    headers = {
        "auth-token": token,
        "Content-Type": "application/json",
    }

    all_records = []
    offset = 0
    limit = 100
    has_more = True

    print("[INFO] Iniciando extracción paginada de registros...")
    while has_more:
        url = f"{API_BASE_URL}/resources/agency/{ORGANIZATION_ID}?first={offset}&limit={limit}"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        batch = response.json().get("agency", [])
        batch_size = len(batch)
        print(f"[INFO] Batch obtenido: {batch_size} registros (Offset: {offset})")

        if batch_size > 0:
            all_records.extend(batch)
            offset += limit

        if batch_size < limit:
            has_more = False

    print(f"[INFO] Extracción finalizada. Total de entidades recuperadas: {len(all_records)}")
    return all_records


def transform_data(records):
    """Estructura, limpia y mapea el esquema relacional de agencias/clientes."""
    if not records:
        return []

    headers = [
        "Status", "External_Code", "Name", "Email",
        "Phone_Number", "Address", "Postal_Code", "Credit_Limit",
        "Document_Number", "City", "Province", "Country",
        "Organization", "Manager_Group", "Agency_Manager_ID"
    ]

    transformed_rows = [headers]

    for item in records:
        row = [
            "ACTIVE" if item.get("active") else "INACTIVE",
            str(item.get("id") or ""),
            str(item.get("name") or ""),
            str(item.get("email") or ""),
            str(item.get("phoneNumber") or ""),
            str(item.get("addressText") or ""),
            str(item.get("postalCode") or ""),
            str(item.get("deferredLimit") or "0"),
            str(item.get("documentNumber") or ""),
            str(item.get("city") or ""),
            str(item.get("province") or ""),
            str(item.get("country") or ""),
            str(ORGANIZATION_ID),
            str(item.get("managementGroup") or ""),
            str(item.get("agencyManagerId") or "")
        ]
        transformed_rows.append(row)

    return transformed_rows


def sync_to_google_sheets(rows):
    """Sincroniza la matriz tabular transformada con la hoja de Google Sheets destino."""
    if not os.path.exists(GOOGLE_CREDS_FILE):
        print("[WARN] Credenciales de Google Sheets no configuradas localmente. Omitiendo sync.")
        return

    print(f"[INFO] Conectando con Google Sheets ({SPREADSHEET_NAME})...")
    gc = gspread.service_account(filename=GOOGLE_CREDS_FILE)
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.get_worksheet(DESTINATION_SHEET_INDEX)

    print("[INFO] Limpiando rango previo y actualizando matriz de datos...")
    worksheet.clear()
    worksheet.update(range_name="A1", values=rows, value_input_option="USER_ENTERED")
    print(f"[INFO] Sincronización exitosa. Filas insertadas: {len(rows)}")


def run_pipeline():
    """Ejecución orquestada del pipeline ETL."""
    try:
        token = authenticate_api()
        raw_agencies = fetch_all_agencies(token)
        matrix = transform_data(raw_agencies)
        sync_to_google_sheets(matrix)
        log_execution_timestamp("SUCCESS")
        print("[INFO] Pipeline ETL completado con éxito.")
    except Exception as err:
        print(f"[FATAL] Error en la ejecución del pipeline: {err}")
        log_execution_timestamp("FAILED")
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()