from typing import Literal, cast

RunStatFailureFailureReasonType0 = Literal[
    "CONNECTION_ERROR", "NON_SUCCESS_STATUS", "QUOTA_EXCEEDED", "SSRF_BLOCKED", "TIMEOUT", "WORKER_LOST"
]

RUN_STAT_FAILURE_FAILURE_REASON_TYPE_0_VALUES: set[RunStatFailureFailureReasonType0] = {
    "CONNECTION_ERROR",
    "NON_SUCCESS_STATUS",
    "QUOTA_EXCEEDED",
    "SSRF_BLOCKED",
    "TIMEOUT",
    "WORKER_LOST",
}


def check_run_stat_failure_failure_reason_type_0(value: str) -> RunStatFailureFailureReasonType0:
    if value in RUN_STAT_FAILURE_FAILURE_REASON_TYPE_0_VALUES:
        return cast(RunStatFailureFailureReasonType0, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {RUN_STAT_FAILURE_FAILURE_REASON_TYPE_0_VALUES!r}")
