from pathlib import Path
import sys
from typing import Any, Dict, Optional

# Ensure project root is in sys.path so 'frontend' package is resolvable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx
import streamlit as st

try:
    from frontend.config import API_V1_PREFIX, BACKEND_API_BASE_URL, TIMEOUT_SECONDS
except ImportError:
    from config import API_V1_PREFIX, BACKEND_API_BASE_URL, TIMEOUT_SECONDS


class APIClient:
    def __init__(self):
        self.base_url = f"{BACKEND_API_BASE_URL}{API_V1_PREFIX}"

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = st.session_state.get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def login(self, username: str, password: str) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/token"
        response = httpx.post(
            url,
            data={"username": username, "password": password},
            timeout=TIMEOUT_SECONDS
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state["access_token"] = data["access_token"]
            st.session_state["current_user"] = data["user"]
            return {"success": True, "user": data["user"]}
        else:
            detail = response.json().get("detail", "Authentication failed")
            return {"success": False, "error": detail}

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = httpx.get(url, headers=self._get_headers(), params=params, timeout=TIMEOUT_SECONDS)
            if response.status_code in [200, 201]:
                return {"success": True, "data": response.json()}
            else:
                err = response.json().get("detail") or response.json().get("message") or response.text
                return {"success": False, "error": err, "status_code": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e), "status_code": 500}

    def post(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = httpx.post(url, headers=self._get_headers(), json=json_data, timeout=TIMEOUT_SECONDS)
            if response.status_code in [200, 201]:
                return {"success": True, "data": response.json()}
            else:
                err = response.json().get("detail") or response.json().get("message") or response.text
                return {"success": False, "error": err, "status_code": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e), "status_code": 500}

    def patch(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = httpx.patch(url, headers=self._get_headers(), json=json_data, timeout=TIMEOUT_SECONDS)
            if response.status_code in [200, 200]:
                return {"success": True, "data": response.json()}
            else:
                err = response.json().get("detail") or response.json().get("message") or response.text
                return {"success": False, "error": err, "status_code": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e), "status_code": 500}


api = APIClient()
