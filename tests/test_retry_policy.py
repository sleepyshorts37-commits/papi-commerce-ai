import pytest

from papi_core.retry_policy import RetryPolicyError, decide_retry


def test_transient_error_uses_exponential_backoff_and_injected_jitter():
    decision = decide_retry(error_code="rate_limited", attempt=2, max_attempts=5,
                            base_delay_seconds=2, jitter_fraction=0.25,
                            jitter_sample=1)
    assert decision.retry is True
    assert decision.delay_seconds == 5.0
    assert decision.reason == "transient_error"


def test_permanent_error_is_not_retried():
    decision = decide_retry(error_code="permission_denied", attempt=1, max_attempts=5)
    assert (decision.retry, decision.delay_seconds, decision.reason) == (
        False, 0.0, "permanent_error"
    )


def test_attempt_limit_stops_retry():
    decision = decide_retry(error_code="service_timeout", attempt=5, max_attempts=5)
    assert decision.retry is False
    assert decision.reason == "attempt_limit_reached"


def test_backoff_is_capped_before_and_after_jitter():
    decision = decide_retry(error_code="connection_reset", attempt=20, max_attempts=25,
                            base_delay_seconds=10, max_delay_seconds=30,
                            jitter_fraction=1, jitter_sample=1)
    assert decision.delay_seconds == 30


@pytest.mark.parametrize("kwargs", [
    {"attempt": 0}, {"attempt": True}, {"max_attempts": 0},
    {"base_delay_seconds": 0}, {"max_delay_seconds": -1},
    {"jitter_fraction": 1.1}, {"jitter_fraction": -0.1},
    {"jitter_sample": 1.1}, {"jitter_sample": -0.1},
])
def test_invalid_parameters_are_rejected(kwargs):
    args = dict(error_code="rate_limited", attempt=1, max_attempts=3)
    args.update(kwargs)
    with pytest.raises(RetryPolicyError):
        decide_retry(**args)


def test_base_delay_cannot_exceed_cap():
    with pytest.raises(RetryPolicyError):
        decide_retry(error_code="rate_limited", attempt=1, max_attempts=3,
                     base_delay_seconds=10, max_delay_seconds=5)


def test_unknown_error_code_is_permanent_by_default():
    decision = decide_retry(error_code="unknown_internal_error", attempt=1, max_attempts=3)
    assert not decision.retry


def test_jitter_zero_is_deterministic():
    first = decide_retry(error_code="temporarily_unavailable", attempt=3,
                         max_attempts=4, jitter_fraction=0, jitter_sample=0)
    second = decide_retry(error_code="temporarily_unavailable", attempt=3,
                          max_attempts=4, jitter_fraction=0, jitter_sample=1)
    assert first.delay_seconds == second.delay_seconds == 8
