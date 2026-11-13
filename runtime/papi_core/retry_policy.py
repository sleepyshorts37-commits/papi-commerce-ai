"""Décision de reprise pure et déterministe pour les travaux PAPI.

Ce module calcule une politique ; il ne dort pas, ne réserve pas de job et
n'effectue aucun appel réseau ou effet métier.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


class RetryPolicyError(ValueError):
    """Paramètre de politique de reprise invalide."""


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    delay_seconds: float
    reason: str


DEFAULT_RETRYABLE_CODES: FrozenSet[str] = frozenset({
    "temporarily_unavailable",
    "rate_limited",
    "connection_reset",
    "service_timeout",
})


def decide_retry(
    *,
    error_code: str,
    attempt: int,
    max_attempts: int,
    base_delay_seconds: float = 2.0,
    max_delay_seconds: float = 3600.0,
    jitter_fraction: float = 0.2,
    jitter_sample: float = 0.5,
    retryable_codes: FrozenSet[str] = DEFAULT_RETRYABLE_CODES,
) -> RetryDecision:
    """Retourne une décision sans side effects.

    attempt est le numéro de tentative qui vient d'échouer (à partir de 1).
    jitter_sample doit être fourni par l'appelant dans [0, 1] pour rendre le
    calcul reproductible et testable. Aucun générateur aléatoire n'est caché.
    """
    if not isinstance(error_code, str) or not error_code or len(error_code) > 80:
        raise RetryPolicyError("error_code invalide")
    if type(attempt) is not int or attempt < 1:
        raise RetryPolicyError("attempt doit être un entier positif")
    if type(max_attempts) is not int or max_attempts < 1:
        raise RetryPolicyError("max_attempts doit être un entier positif")
    for name, value in (("base_delay_seconds", base_delay_seconds),
                        ("max_delay_seconds", max_delay_seconds)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise RetryPolicyError(name + " doit être positif")
    if base_delay_seconds > max_delay_seconds:
        raise RetryPolicyError("base_delay_seconds dépasse max_delay_seconds")
    if isinstance(jitter_fraction, bool) or not isinstance(jitter_fraction, (int, float)) or not 0 <= jitter_fraction <= 1:
        raise RetryPolicyError("jitter_fraction doit être compris entre 0 et 1")
    if isinstance(jitter_sample, bool) or not isinstance(jitter_sample, (int, float)) or not 0 <= jitter_sample <= 1:
        raise RetryPolicyError("jitter_sample doit être compris entre 0 et 1")
    if not isinstance(retryable_codes, (set, frozenset)) or any(
        not isinstance(code, str) or not code for code in retryable_codes
    ):
        raise RetryPolicyError("retryable_codes invalide")

    if error_code not in retryable_codes:
        return RetryDecision(False, 0.0, "permanent_error")
    if attempt >= max_attempts:
        return RetryDecision(False, 0.0, "attempt_limit_reached")

    exponent = min(attempt - 1, 60)
    raw_delay = min(float(max_delay_seconds), float(base_delay_seconds) * (2 ** exponent))
    jitter_multiplier = (1.0 - float(jitter_fraction)) + (
        2.0 * float(jitter_fraction) * float(jitter_sample)
    )
    delay = min(float(max_delay_seconds), raw_delay * jitter_multiplier)
    return RetryDecision(True, delay, "transient_error")
