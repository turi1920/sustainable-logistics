# Deployment & Local Development Guide

## 1. Local Development Quickstart

### Prerequisites
- Python 3.10+
- Git

### Installation
```bash
# 1. Clone repository
git clone <repository_url>
cd sustainable-reverse-logistics

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.\.venv\Scripts\Activate.ps1    # On Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Seed demonstration dataset
export PYTHONPATH=.             # On Linux/macOS
$env:PYTHONPATH="."             # On Windows PowerShell
python scripts/seed_demo_data.py
```

### Running Backend API
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open interactive OpenAPI Swagger UI at `http://localhost:8000/docs`.

### Running Streamlit Frontend
```bash
streamlit run frontend/app.py --server.port 8501
```
Open browser at `http://localhost:8501`.

---

## 2. Docker & Containerized Deployment

Run the complete multi-container stack (PostgreSQL + FastAPI + Streamlit):
```bash
docker compose up -d --build
```
- **Streamlit Web Portal:** `http://localhost:8501`
- **FastAPI Backend:** `http://localhost:8000/docs`
- **PostgreSQL Database:** `localhost:5432`

---

## 3. Running Automated Tests & Coverage

```bash
# Run complete pytest test suite
pytest -v backend/tests

# Run test coverage report
pytest --cov=backend/app backend/tests
```

---

## 4. Default Demo Accounts

| Role | Email | Password |
| :--- | :--- | :--- |
| **Platform Administrator** | `admin@reverse-logistics.com` | `password123` |
| **Return Agent (Field)** | `agent@reverse-logistics.com` | `password123` |
| **Operations Specialist** | `ops@reverse-logistics.com` | `password123` |
| **Apex Approver (Manufacturer)**| `approver@apex.com` | `password123` |
| **Finance & Sustainability** | `analyst@reverse-logistics.com` | `password123` |
