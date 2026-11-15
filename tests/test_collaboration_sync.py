import unittest

from papi_core.collaboration_sync import (
    CollaborationSyncError,
    build_live_collaboration_preview,
)
from papi_core.principal import _issue_authenticated_agent_principal


class FakeRemoteStore:
    def __init__(self, memory_pages=None, message_pages=None):
        self.memory_pages = memory_pages or []
        self.message_pages = message_pages or []
        self.memory_calls = []
        self.message_calls = []

    @staticmethod
    def _page(pages, calls, cursor):
        calls.append(cursor)
        index = len(calls) - 1
        if index >= len(pages):
            return {"items": [], "next_cursor": None}
        return pages[index]

    def search_memory(self, *, principal, limit, cursor=None):
        return self._page(self.memory_pages, self.memory_calls, cursor)

    def read_messages(self, *, principal, limit, cursor=None):
        return self._page(self.message_pages, self.message_calls, cursor)


class CollaborationSyncPreviewTests(unittest.TestCase):
    def setUp(self):
        self.principal = _issue_authenticated_agent_principal("astou")
        self.memory = {
            "memory_id": "MEM-1", "event_type": "remember", "scope": "shared",
            "sensitivity": "normal", "category": "fact", "title": "Règle",
            "content": "Mémoire partagée.", "source_type": "task",
            "source_id": "TASK-1", "confidence": 0.9, "tags": [],
        }
        self.message = {
            "message_id": "MSG-00000000000000000000000000000001",
            "sender": "astou", "recipient": "all", "subject": "Info",
            "body": "Message interne.", "message_type": "info",
        }

    def test_complete_paginated_snapshot_is_preview_only(self):
        remote = FakeRemoteStore(
            memory_pages=[
                {"items": [], "next_cursor": "memory-page-2"},
                {"items": [self.memory], "next_cursor": None},
            ],
            message_pages=[
                {"items": [self.message], "next_cursor": None},
            ],
        )
        result = build_live_collaboration_preview(
            principal=self.principal, local_memory=[self.memory],
            local_messages=[self.message], remote_store=remote, page_size=1,
        )
        self.assertEqual(result["preview"]["counts"]["identical"], 2)
        self.assertTrue(result["remote_snapshot"]["complete"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["sync_enabled"])
        self.assertEqual(remote.memory_calls, [None, "memory-page-2"])

    def test_repeated_cursor_fails_closed(self):
        remote = FakeRemoteStore(
            memory_pages=[
                {"items": [], "next_cursor": "same"},
                {"items": [], "next_cursor": "same"},
            ],
            message_pages=[{"items": [], "next_cursor": None}],
        )
        with self.assertRaises(CollaborationSyncError):
            build_live_collaboration_preview(
                principal=self.principal, local_memory=[], local_messages=[],
                remote_store=remote, page_size=1,
            )

    def test_repeated_record_across_pages_fails_closed(self):
        remote = FakeRemoteStore(
            memory_pages=[
                {"items": [self.memory], "next_cursor": "next"},
                {"items": [self.memory], "next_cursor": None},
            ],
            message_pages=[{"items": [], "next_cursor": None}],
        )
        with self.assertRaises(CollaborationSyncError):
            build_live_collaboration_preview(
                principal=self.principal, local_memory=[], local_messages=[],
                remote_store=remote, page_size=1,
            )

    def test_page_cap_refuses_incomplete_snapshot(self):
        remote = FakeRemoteStore(
            memory_pages=[{"items": [], "next_cursor": "more"}],
            message_pages=[],
        )
        with self.assertRaises(CollaborationSyncError):
            build_live_collaboration_preview(
                principal=self.principal, local_memory=[], local_messages=[],
                remote_store=remote, page_size=1, max_pages=1,
            )

    def test_invalid_page_payload_is_rejected(self):
        remote = FakeRemoteStore(
            memory_pages=[{"items": "not-a-list", "next_cursor": None}],
            message_pages=[],
        )
        with self.assertRaises(CollaborationSyncError):
            build_live_collaboration_preview(
                principal=self.principal, local_memory=[], local_messages=[],
                remote_store=remote,
            )

    def test_missing_adapter_is_rejected(self):
        with self.assertRaises(CollaborationSyncError):
            build_live_collaboration_preview(
                principal=self.principal, local_memory=[], local_messages=[],
                remote_store=None,
            )


if __name__ == "__main__":
    unittest.main()
