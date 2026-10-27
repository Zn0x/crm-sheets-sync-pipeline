# 🔄 CRM to Google Sheets Sync Pipeline (ETL)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![REST API](https://img.shields.io/badge/REST_API-Pagination-orange?style=for-the-badge&logo=fastapi&logoColor=white)
![ETL Pipeline](https://img.shields.io/badge/Architecture-ETL-brightgreen?style=for-the-badge)
![Google Cloud](https://img.shields.io/badge/Google%20Sheets-API-yellow?style=for-the-badge&logo=google-sheets&logoColor=white)

An automated serverless ETL (Extract, Transform, Load) data pipeline that authenticates against enterprise RESTful endpoints, handles stateful token authentication, manages iterative cursor pagination to extract thousands of client records, and synchronizes normalized business datasets with Google Sheets for BI dashboards.

---

## ⚡ Architecture & Pipeline Stages

1. **Extract (Authentication & Pagination):**
   - Authenticates against token-based authentication endpoints.
   - Handles API pagination using sliding cursor windows (`offset` / `limit`), preventing connection timeouts and payload drops.
2. **Transform (Schema Mapping & Normalization):**
   - Sanitizes raw JSON documents into structured matrix formats.
   - Cleans missing fields, formats booleans, and casts identifier types.
3. **Load (Cloud Synchronization):**
   - Employs `gspread` and Google Cloud Service Accounts to atomically clear and batch-update destination sheets.
   - Emits timestamped audit logging rows for operational observability.

---

## 🛠️ Tech Stack

- **Language:** Python
- **HTTP Client:** `requests` (Session management & error handling)
- **Cloud API:** `gspread` (Google Sheets Service Account Auth)
- **CI/CD Orchestration:** GitHub Actions (Automated cron triggers)

---

## 🚀 Setup & Execution

### 1. Installation
```bash
git clone [https://github.com/Zn0x/crm-sheets-sync-pipeline.git](https://github.com/Zn0x/crm-sheets-sync-pipeline.git)
cd crm-sheets-sync-pipeline
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

---
##2. Environment Variables
---
cp .env.example .env

---
## 3. Run pipeline
--

python main.py

---

### 6. `.github/workflows/run-etl.yml` (CI/CD programado con Secrets)

```yaml
name: Scheduled CRM Sync Pipeline

on:
  schedule:
    # Se ejecuta todos los días a las 08:00 UTC
    - cron: '0 8 * * *'
  workflow_dispatch: # Disparo manual desde botón en GitHub

jobs:
  run-etl:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run ETL Script
        env:
          API_BASE_URL: ${{ secrets.API_BASE_URL }}
          API_USERNAME: ${{ secrets.API_USERNAME }}
          API_PASSWORD: ${{ secrets.API_PASSWORD }}
          ORGANIZATION_ID: ${{ secrets.ORGANIZATION_ID }}
          SPREADSHEET_NAME: ${{ secrets.SPREADSHEET_NAME }}
          DESTINATION_SHEET_INDEX: ${{ secrets.DESTINATION_SHEET_INDEX }}
          AUDIT_LOGS_SHEET: ${{ secrets.AUDIT_LOGS_SHEET }}
          GOOGLE_CREDS_FILE: 'credentials.json'
        run: |
          python main.py