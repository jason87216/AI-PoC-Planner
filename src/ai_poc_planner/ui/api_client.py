"""Safe, thin client for the local FastAPI product boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx


class ApiClientError(RuntimeError):
    """A public API failure represented by a safe, user-facing message."""

    def __init__(self, code: str, user_message: str) -> None:
        self.code = code
        self.user_message = user_message
        super().__init__(user_message)


_USER_MESSAGES = {
    "provider_not_ready": "尚未有可用的已測試模型設定。",
    "provider_profile_mismatch": "目前模型設定不適用於這份規劃，請重新選擇並測試模型。",
    "provider_output_invalid": "模型暫時無法產生可用結果，請稍後再試。",
    "analysis_not_ready": "訪談尚未完成，暫時無法開始評估。",
    "analysis_not_found": "尚未找到這份規劃的評估結果。",
    "analysis_already_exists": "這份規劃已有評估結果，已保留原有內容。",
    "report_not_ready": "請先完成評估，再產生規劃報告。",
    "report_not_found": "尚未找到這份規劃的報告。",
    "report_already_exists": "這份規劃已有報告，已保留原有內容。",
    "completed_version_immutable": "這份已完成的規劃無法再修改。",
    "model_profile_not_found": "找不到指定的模型設定。",
    "project_not_found": "找不到指定的專案。",
    "project_version_not_found": "找不到這個專案版本。",
    "invalid_interview_transition": "目前狀態無法執行這項操作，請重新整理後再試。",
    "interview_answers_incomplete": "請完成本輪每一題，或選擇不知道。",
    "interview_question_already_answered": "這一輪已經提交，請重新整理後繼續。",
    "interview_round_limit_reached": "訪談已達既有上限，請依目前狀態繼續。",
    "fact_correction_invalid": "修正內容不完整或無法套用，請檢查後再試。",
    "fact_correction_required": "這項已確認資訊需要使用明確修正方式更新。",
    "understanding_already_confirmed": "需求理解已確認。",
    "understanding_confirmation_required": "請先確認或修正目前的需求理解。",
    "internal_error": "服務暫時無法完成此操作，請稍後再試。",
}


class ApiClient:
    """Call product endpoints without importing application or persistence code."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url or "http://127.0.0.1:8000",
            timeout=httpx.Timeout(120.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
        )

    def list_projects(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/v1/projects")
        return self._list_of_objects(payload)

    def provider_status(self) -> dict[str, Any]:
        return self._object(self._request("GET", "/v1/provider-status"))

    def list_profiles(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/v1/model-profiles")
        return self._list_of_objects(payload)

    def create_profile(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._object(self._request("POST", "/v1/model-profiles", payload))

    def update_profile(
        self, profile_id: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        return self._object(
            self._request("PATCH", f"/v1/model-profiles/{profile_id}", payload)
        )

    def delete_profile(self, profile_id: str) -> None:
        self._request("DELETE", f"/v1/model-profiles/{profile_id}", expected={204})

    def select_profile(self, profile_id: str) -> dict[str, Any]:
        return self._object(
            self._request("POST", f"/v1/model-profiles/{profile_id}/select")
        )

    def test_profile(self, profile_id: str) -> dict[str, Any]:
        return self._object(
            self._request("POST", f"/v1/model-profiles/{profile_id}/test")
        )

    def create_discovery_project(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._object(self._request("POST", "/v1/discovery-projects", payload))

    def get_discovery_session(
        self, project_id: str, version_number: int
    ) -> dict[str, Any]:
        return self._object(
            self._request(
                "GET", self._discovery_path(project_id, version_number, "discovery")
            )
        )

    def generate_understanding(
        self, project_id: str, version_number: int
    ) -> dict[str, Any]:
        return self._object(
            self._request(
                "POST",
                self._discovery_path(project_id, version_number, "understanding"),
            )
        )

    def confirm_understanding(
        self, project_id: str, version_number: int
    ) -> dict[str, Any]:
        return self._object(
            self._request(
                "POST",
                self._discovery_path(
                    project_id, version_number, "understanding/confirm"
                ),
            )
        )

    def submit_understanding_corrections(
        self, project_id: str, version_number: int, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        return self._object(
            self._request(
                "POST",
                self._discovery_path(
                    project_id, version_number, "understanding/corrections"
                ),
                payload,
            )
        )

    def submit_understanding_feedback(
        self, project_id: str, version_number: int, feedback: str
    ) -> dict[str, Any]:
        return self._object(
            self._request(
                "POST",
                self._discovery_path(
                    project_id, version_number, "understanding/feedback"
                ),
                {"feedback": feedback},
            )
        )

    def generate_interview_round(
        self, project_id: str, version_number: int
    ) -> list[dict[str, Any]]:
        return self._list_of_objects(
            self._request(
                "POST",
                self._discovery_path(project_id, version_number, "interview-rounds"),
            )
        )

    def list_interview_questions(
        self, project_id: str, version_number: int
    ) -> list[dict[str, Any]]:
        return self._list_of_objects(
            self._request(
                "GET",
                self._discovery_path(project_id, version_number, "interview-questions"),
            )
        )

    def submit_interview_answers(
        self, project_id: str, version_number: int, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        return self._object(
            self._request(
                "POST",
                self._discovery_path(project_id, version_number, "interview-answers"),
                payload,
            )
        )

    def list_visible_messages(
        self, project_id: str, version_number: int
    ) -> list[dict[str, Any]]:
        return self._list_of_objects(
            self._request(
                "GET", self._discovery_path(project_id, version_number, "messages")
            )
        )

    def list_current_facts(
        self, project_id: str, version_number: int
    ) -> list[dict[str, Any]]:
        return self._list_of_objects(
            self._request(
                "GET", self._discovery_path(project_id, version_number, "facts")
            )
        )

    def get_project_version(
        self, project_id: str, version_number: int
    ) -> dict[str, Any]:
        return self._object(
            self._request("GET", self._version_path(project_id, version_number))
        )

    def create_analysis(self, project_id: str, version_number: int) -> dict[str, Any]:
        return self._object(
            self._request(
                "POST", self._version_path(project_id, version_number, "analysis")
            )
        )

    def get_analysis(self, project_id: str, version_number: int) -> dict[str, Any]:
        return self._object(
            self._request(
                "GET", self._version_path(project_id, version_number, "analysis")
            )
        )

    def create_report(self, project_id: str, version_number: int) -> dict[str, Any]:
        return self._object(
            self._request(
                "POST", self._version_path(project_id, version_number, "report")
            )
        )

    def get_report(self, project_id: str, version_number: int) -> dict[str, Any]:
        return self._object(
            self._request(
                "GET", self._version_path(project_id, version_number, "report")
            )
        )

    @staticmethod
    def _discovery_path(project_id: str, version_number: int, suffix: str) -> str:
        return ApiClient._version_path(project_id, version_number, suffix)

    @staticmethod
    def _version_path(
        project_id: str, version_number: int, suffix: str | None = None
    ) -> str:
        path = f"/v1/projects/{project_id}/versions/{version_number}"
        return f"{path}/{suffix}" if suffix else path

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        expected: set[int] | None = None,
    ) -> object:
        expected = expected or {200, 201}
        try:
            response = self._client.request(method, path, json=payload)
        except httpx.HTTPError as error:
            raise ApiClientError(
                "api_unavailable", "目前無法連線到本機服務，請稍後再試。"
            ) from error
        if response.status_code not in expected:
            raise self._error_from_response(response)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise ApiClientError(
                "invalid_response", "服務回應格式無法使用，請稍後再試。"
            ) from error

    @staticmethod
    def _object(payload: object) -> dict[str, Any]:
        if isinstance(payload, dict) and all(isinstance(key, str) for key in payload):
            return payload
        raise ApiClientError("invalid_response", "服務回應格式無法使用，請稍後再試。")

    @staticmethod
    def _list_of_objects(payload: object) -> list[dict[str, Any]]:
        if isinstance(payload, list) and all(
            isinstance(item, dict) for item in payload
        ):
            return payload
        raise ApiClientError("invalid_response", "服務回應格式無法使用，請稍後再試。")

    @staticmethod
    def _error_from_response(response: httpx.Response) -> ApiClientError:
        code = "internal_error"
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict) and isinstance(error.get("code"), str):
                    code = error["code"]
        except ValueError:
            pass
        return ApiClientError(
            code, _USER_MESSAGES.get(code, _USER_MESSAGES["internal_error"])
        )
