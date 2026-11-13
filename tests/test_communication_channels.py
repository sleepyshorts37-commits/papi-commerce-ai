import asyncio
import unittest

from papi_core.communication_channels import (
    CommunicationChannelError, DeliveryReceipt, InvalidChannelPayloadError,
    OwnerEmailNotification, ProviderTimeoutError, SpeechAudio, SpeechRequest,
    SpeechTranscript, SynthesisRequest, call_provider, validate_owner_notification,
    validate_speech_audio, validate_speech_request, validate_synthesis_request,
    validate_transcript,
)


class CommunicationChannelContractTests(unittest.TestCase):
    def test_valid_speech_request(self):
        validate_speech_request(SpeechRequest(b"audio", "audio/wav", "fr-FR"))

    def test_rejects_empty_or_unsupported_audio(self):
        with self.assertRaises(InvalidChannelPayloadError):
            validate_speech_request(SpeechRequest(b"", "audio/wav"))
        with self.assertRaises(InvalidChannelPayloadError):
            validate_speech_request(SpeechRequest(b"audio", "application/octet-stream"))

    def test_transcript_rejects_secrets(self):
        with self.assertRaises(InvalidChannelPayloadError):
            validate_transcript(SpeechTranscript("api_key=supersecret"))

    def test_valid_synthesis_and_audio(self):
        validate_synthesis_request(SynthesisRequest("Bonjour.", "astou-fr"))
        validate_speech_audio(SpeechAudio(b"voice", "audio/mpeg"))

    def test_synthesis_rejects_secret_and_invalid_profile(self):
        with self.assertRaises(InvalidChannelPayloadError):
            validate_synthesis_request(SynthesisRequest("token=abc", "astou-fr"))
        with self.assertRaises(InvalidChannelPayloadError):
            validate_synthesis_request(SynthesisRequest("Bonjour", "../profile"))

    def _notification(self, **changes):
        fields = dict(
            notification_id="notif-1", agent_id="astou", priority="P1",
            reason_code="decision_required", subject="Décision requise",
            body="Une validation est nécessaire.", correlation_id="corr-1",
            idempotency_key="idem-1", created_at="2026-11-13T12:00:00Z",
        )
        fields.update(changes)
        return OwnerEmailNotification(**fields)

    def test_owner_notification_contract(self):
        validate_owner_notification(self._notification())

    def test_rejects_non_owner_destination_and_secret(self):
        with self.assertRaises(InvalidChannelPayloadError):
            validate_owner_notification(self._notification(recipient_class="customer"))
        with self.assertRaises(InvalidChannelPayloadError):
            validate_owner_notification(self._notification(body="password=secret123"))

    def test_provider_timeout_is_typed(self):
        async def slow():
            await asyncio.sleep(0.2)
        with self.assertRaises(ProviderTimeoutError):
            asyncio.run(call_provider(slow(), timeout_seconds=0.1))

    def test_provider_failure_is_normalized(self):
        async def fail():
            raise OSError("private provider detail")
        with self.assertRaises(CommunicationChannelError):
            asyncio.run(call_provider(fail(), timeout_seconds=1))


if __name__ == "__main__":
    unittest.main()
