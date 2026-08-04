"""State-aware recovery for ambiguous local analysis and report writes."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from ai_poc_planner.ui.api_client import ApiClient, ApiClientError

AMBIGUOUS_WRITE_CODES = frozenset({"local_service_timeout", "api_unavailable"})
STATE_RELOAD_ACTION = (
    "請重新整理專案狀態；系統會先讀取已保存結果，不會重複執行已完成的階段。"
)


class RecoveryOperation(StrEnum):
    ANALYSIS = "analysis"
    REPORT = "report"


class RecoveryAction(StrEnum):
    RETRY_ANALYSIS = "retry_analysis"
    CONTINUE_REPORT_ONLY = "continue_report_only"
    RETRY_REPORT_ONLY = "retry_report_only"
    OPEN_PERSISTED_RESULT = "open_persisted_result"
    FAIL_CLOSED = "fail_closed"


def recovery_action_for_status(
    operation: RecoveryOperation | str, persisted_status: object
) -> RecoveryAction:
    """Choose the next safe action using only the durable project status."""

    operation = RecoveryOperation(operation)
    status = str(persisted_status)
    if operation is RecoveryOperation.ANALYSIS:
        return {
            "ready_for_assessment": RecoveryAction.RETRY_ANALYSIS,
            "assessed": RecoveryAction.CONTINUE_REPORT_ONLY,
            "proposal_generated": RecoveryAction.OPEN_PERSISTED_RESULT,
            "complete": RecoveryAction.OPEN_PERSISTED_RESULT,
        }.get(status, RecoveryAction.FAIL_CLOSED)
    return {
        "assessed": RecoveryAction.RETRY_REPORT_ONLY,
        "proposal_generated": RecoveryAction.OPEN_PERSISTED_RESULT,
        "complete": RecoveryAction.OPEN_PERSISTED_RESULT,
    }.get(status, RecoveryAction.FAIL_CLOSED)


class StateAwareApiClient(ApiClient):
    """Avoid replaying writes when a local timeout hides a committed result."""

    def create_analysis(self, project_id: str, version_number: int) -> dict[str, Any]:
        action = self._current_action(
            RecoveryOperation.ANALYSIS, project_id, version_number
        )
        if action in {
            RecoveryAction.CONTINUE_REPORT_ONLY,
            RecoveryAction.OPEN_PERSISTED_RESULT,
        }:
            return ApiClient.get_analysis(self, project_id, version_number)
        if action is not RecoveryAction.RETRY_ANALYSIS:
            raise self._state_error(RecoveryOperation.ANALYSIS)

        try:
            return ApiClient.create_analysis(self, project_id, version_number)
        except ApiClientError as error:
            if error.code not in AMBIGUOUS_WRITE_CODES:
                raise
            return self._recover_analysis(project_id, version_number, error)

    def create_report(self, project_id: str, version_number: int) -> dict[str, Any]:
        action = self._current_action(
            RecoveryOperation.REPORT, project_id, version_number
        )
        if action is RecoveryAction.OPEN_PERSISTED_RESULT:
            return ApiClient.get_report(self, project_id, version_number)
        if action is not RecoveryAction.RETRY_REPORT_ONLY:
            raise self._state_error(RecoveryOperation.REPORT)

        try:
            return ApiClient.create_report(self, project_id, version_number)
        except ApiClientError as error:
            if error.code not in AMBIGUOUS_WRITE_CODES:
                raise
            return self._recover_report(project_id, version_number, error)

    def _current_action(
        self,
        operation: RecoveryOperation,
        project_id: str,
        version_number: int,
    ) -> RecoveryAction:
        try:
            version = ApiClient.get_project_version(self, project_id, version_number)
        except ApiClientError as error:
            if error.code in AMBIGUOUS_WRITE_CODES:
                raise self._ambiguous_error(error) from error
            raise
        return recovery_action_for_status(operation, version.get("status"))

    def _recover_analysis(
        self,
        project_id: str,
        version_number: int,
        original_error: ApiClientError,
    ) -> dict[str, Any]:
        action = self._action_after_ambiguous_write(
            RecoveryOperation.ANALYSIS,
            project_id,
            version_number,
            original_error,
        )
        if action in {
            RecoveryAction.CONTINUE_REPORT_ONLY,
            RecoveryAction.OPEN_PERSISTED_RESULT,
        }:
            try:
                return ApiClient.get_analysis(self, project_id, version_number)
            except ApiClientError as error:
                if error.code in AMBIGUOUS_WRITE_CODES:
                    raise self._ambiguous_error(original_error) from error
                raise
        if action is RecoveryAction.RETRY_ANALYSIS:
            raise self._ambiguous_error(original_error) from original_error
        raise self._state_error(RecoveryOperation.ANALYSIS) from original_error

    def _recover_report(
        self,
        project_id: str,
        version_number: int,
        original_error: ApiClientError,
    ) -> dict[str, Any]:
        action = self._action_after_ambiguous_write(
            RecoveryOperation.REPORT,
            project_id,
            version_number,
            original_error,
        )
        if action is RecoveryAction.OPEN_PERSISTED_RESULT:
            try:
                return ApiClient.get_report(self, project_id, version_number)
            except ApiClientError as error:
                if error.code in AMBIGUOUS_WRITE_CODES:
                    raise self._ambiguous_error(original_error) from error
                raise
        if action is RecoveryAction.RETRY_REPORT_ONLY:
            raise self._ambiguous_error(original_error) from original_error
        raise self._state_error(RecoveryOperation.REPORT) from original_error

    def _action_after_ambiguous_write(
        self,
        operation: RecoveryOperation,
        project_id: str,
        version_number: int,
        original_error: ApiClientError,
    ) -> RecoveryAction:
        try:
            version = ApiClient.get_project_version(self, project_id, version_number)
        except ApiClientError as reload_error:
            raise self._ambiguous_error(original_error) from reload_error
        return recovery_action_for_status(operation, version.get("status"))

    @staticmethod
    def _ambiguous_error(error: ApiClientError) -> ApiClientError:
        return ApiClientError(
            error.code,
            error.user_message,
            retryable=True,
            user_action=STATE_RELOAD_ACTION,
        )

    @staticmethod
    def _state_error(operation: RecoveryOperation) -> ApiClientError:
        stage = "評估" if operation is RecoveryOperation.ANALYSIS else "報告"
        return ApiClientError(
            "persisted_state_conflict",
            f"已保存的專案狀態無法安全繼續{stage}。",
            retryable=False,
            user_action="請重新整理後從專案歷史重新開啟；若問題持續發生，請查看本機啟動日誌。",
        )
