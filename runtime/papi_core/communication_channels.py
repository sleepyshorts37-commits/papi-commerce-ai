"""Interfaces injectables pour les canaux voix et e-mail du propriétaire.

Aucun fournisseur réseau n'est inclus. Les adaptateurs concrets doivent être
injectés explicitement par une couche de composition de confiance.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Protocol, TypeVar

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_TRANSCRIPT_CHARS = 8_000
MAX_SPEECH_CHARS = 8_000
MAX_EMAIL_SUBJECT_CHARS = 160
MAX_EMAIL_BODY_CHARS = 8_000
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 20.0
SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|token|password|passwd|secret|"
    r"otp|pin|cvv|authorization)\s*[:=]\s*\S+|"
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,})\b"
)


class CommunicationChannelError(RuntimeError):
    """Erreur de contrat ou d'exécution d'un canal de communication."""


class ProviderTimeoutError(CommunicationChannelError):
    """Le fournisseur injecté n'a pas répondu dans le délai imparti."""


class ProviderUnavailableError(CommunicationChannelError):
    """Le fournisseur injecté est indisponible ou a échoué."""


class InvalidChannelPayloadError(CommunicationChannelError):
    """Le contenu transmis au canal ne respecte pas son contrat."""


@dataclass(frozen=True)
class SpeechRequest:
    audio: bytes
    content_type: str
    language: str | None = None


@dataclass(frozen=True)
class SpeechTranscript:
    text: str
    language: str | None = None


@dataclass(frozen=True)
class SynthesisRequest:
    text: str
    voice_profile_id: str


@dataclass(frozen=True)
class SpeechAudio:
    audio: bytes
    content_type: str


@dataclass(frozen=True)
class OwnerEmailNotification:
    """Notification au propriétaire ; aucune adresse arbitraire n'est acceptée."""
    notification_id: str
    agent_id: str
    priority: str
    reason_code: str
    subject: str
    body: str
    correlation_id: str
    idempotency_key: str
    created_at: str
    evidence_refs: tuple[str, ...] = ()
    requires_owner_action: bool = False
    deadline: str | None = None
    recipient_class: str = "owner"


@dataclass(frozen=True)
class DeliveryReceipt:
    provider_message_id: str
    accepted_at: str


class SpeechToText(Protocol):
    async def transcribe(self, request: SpeechRequest) -> SpeechTranscript:
        """Transcrit un audio fourni explicitement par l'utilisateur."""


class TextToSpeech(Protocol):
    async def synthesize(self, request: SynthesisRequest) -> SpeechAudio:
        """Produit une voix synthétique autorisée pour un profil donné."""


class OwnerEmailSender(Protocol):
    async def send_owner_notification(
        self, notification: OwnerEmailNotification
    ) -> DeliveryReceipt:
        """Résout le destinataire depuis une configuration serveur vérifiée."""


T = TypeVar("T")


async def call_provider(operation, *, timeout_seconds: float = DEFAULT_PROVIDER_TIMEOUT_SECONDS) -> T:
    """Exécute une coroutine fournisseur avec délai borné et erreurs normalisées."""
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise InvalidChannelPayloadError("Délai fournisseur invalide.")
    if not 0.1 <= timeout_seconds <= 120:
        raise InvalidChannelPayloadError("Le délai doit être compris entre 0,1 et 120 secondes.")
    try:
        return await asyncio.wait_for(operation, timeout=float(timeout_seconds))
    except asyncio.TimeoutError as exc:
        raise ProviderTimeoutError("Délai du fournisseur dépassé.") from exc
    except CommunicationChannelError:
        raise
    except Exception as exc:
        raise ProviderUnavailableError("Le fournisseur de communication a échoué.") from exc


def validate_speech_request(request: SpeechRequest) -> None:
    if not isinstance(request, SpeechRequest) or not isinstance(request.audio, bytes):
        raise InvalidChannelPayloadError("Audio invalide.")
    if not request.audio or len(request.audio) > MAX_AUDIO_BYTES:
        raise InvalidChannelPayloadError("Taille audio vide ou supérieure à 10 Mio.")
    if not isinstance(request.content_type, str) or request.content_type not in {
        "audio/wav", "audio/mpeg", "audio/mp4", "audio/webm", "audio/ogg"
    }:
        raise InvalidChannelPayloadError("Type audio non pris en charge.")
    if request.language is not None and (
        not isinstance(request.language, str) or len(request.language) > 20
    ):
        raise InvalidChannelPayloadError("Code de langue invalide.")


def validate_transcript(transcript: SpeechTranscript) -> None:
    if not isinstance(transcript, SpeechTranscript) or not isinstance(transcript.text, str):
        raise InvalidChannelPayloadError("Transcription invalide.")
    if not transcript.text.strip() or len(transcript.text) > MAX_TRANSCRIPT_CHARS:
        raise InvalidChannelPayloadError("Transcription vide ou trop longue.")
    if SECRET_PATTERN.search(transcript.text):
        raise InvalidChannelPayloadError("La transcription contient un secret apparent.")


def validate_synthesis_request(request: SynthesisRequest) -> None:
    if not isinstance(request, SynthesisRequest):
        raise InvalidChannelPayloadError("Demande de synthèse invalide.")
    if not isinstance(request.text, str) or not request.text.strip() or len(request.text) > MAX_SPEECH_CHARS:
        raise InvalidChannelPayloadError("Texte vide ou trop long pour la synthèse.")
    if SECRET_PATTERN.search(request.text):
        raise InvalidChannelPayloadError("Le texte contient un secret apparent.")
    if not isinstance(request.voice_profile_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", request.voice_profile_id):
        raise InvalidChannelPayloadError("Identifiant de profil vocal invalide.")


def validate_speech_audio(audio: SpeechAudio) -> None:
    if not isinstance(audio, SpeechAudio) or not isinstance(audio.audio, bytes) or not audio.audio:
        raise InvalidChannelPayloadError("Audio synthétisé invalide.")
    if len(audio.audio) > MAX_AUDIO_BYTES:
        raise InvalidChannelPayloadError("Audio synthétisé trop volumineux.")
    if audio.content_type not in {"audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg"}:
        raise InvalidChannelPayloadError("Format audio de sortie invalide.")


def validate_owner_notification(notification: OwnerEmailNotification) -> None:
    if not isinstance(notification, OwnerEmailNotification):
        raise InvalidChannelPayloadError("Notification e-mail invalide.")
    if notification.recipient_class != "owner":
        raise InvalidChannelPayloadError("Seul le propriétaire est accepté par cette interface.")
    for name in ("notification_id", "agent_id", "reason_code", "correlation_id",
                 "idempotency_key", "created_at"):
        value = getattr(notification, name)
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise InvalidChannelPayloadError(f"Champ {name} invalide.")
    if notification.priority not in {"P0", "P1", "P2", "P3"}:
        raise InvalidChannelPayloadError("Priorité invalide.")
    if not isinstance(notification.evidence_refs, tuple) or len(notification.evidence_refs) > 20 or any(not isinstance(ref, str) or not ref.strip() or len(ref) > 500 for ref in notification.evidence_refs):
        raise InvalidChannelPayloadError("Références de preuve invalides.")
    if not isinstance(notification.requires_owner_action, bool):
        raise InvalidChannelPayloadError("requires_owner_action doit être booléen.")
    if notification.deadline is not None and (not isinstance(notification.deadline, str) or len(notification.deadline) > 80):
        raise InvalidChannelPayloadError("Échéance invalide.")
    if not isinstance(notification.subject, str) or not 1 <= len(notification.subject.strip()) <= MAX_EMAIL_SUBJECT_CHARS:
        raise InvalidChannelPayloadError("Sujet e-mail invalide.")
    if not isinstance(notification.body, str) or not 1 <= len(notification.body.strip()) <= MAX_EMAIL_BODY_CHARS:
        raise InvalidChannelPayloadError("Corps e-mail invalide.")
    if SECRET_PATTERN.search(notification.subject + "\n" + notification.body):
        raise InvalidChannelPayloadError("La notification contient un secret apparent.")
