import unittest

from papi_core.video_tasks import (
    DEFAULT_AGENT_IDS,
    VideoTaskError,
    build_video_report,
    create_video_task,
    extract_youtube_video_id,
    validate_video_task,
    validate_video_task_registry,
)


class VideoTaskTests(unittest.TestCase):
    def make_task(self):
        return create_video_task(
            task_id="video-001",
            url="https://www.youtube.com/watch?v=abcdefghijk",
            submitted_by="owner",
            created_at="2026-11-13T22:00:00Z",
        )

    def test_accepts_watch_short_and_embed_links(self):
        self.assertEqual(extract_youtube_video_id("https://www.youtube.com/watch?v=abcdefghijk"), "abcdefghijk")
        self.assertEqual(extract_youtube_video_id("https://youtu.be/abcdefghijk"), "abcdefghijk")
        self.assertEqual(extract_youtube_video_id("https://www.youtube.com/shorts/abcdefghijk"), "abcdefghijk")
        self.assertEqual(extract_youtube_video_id("https://www.youtube.com/embed/abcdefghijk"), "abcdefghijk")

    def test_rejects_non_youtube_and_insecure_links(self):
        for url in ("http://youtube.com/watch?v=abcdefghijk", "https://example.org/watch?v=abcdefghijk"):
            with self.assertRaises(VideoTaskError):
                extract_youtube_video_id(url)

    def test_creates_exactly_ten_agent_subtasks(self):
        task = self.make_task()
        self.assertEqual(len(task["agents"]), 10)
        self.assertEqual(tuple(agent["agent_id"] for agent in task["agents"]), DEFAULT_AGENT_IDS)
        self.assertEqual(validate_video_task(task), [])

    def test_rejects_wrong_team_size(self):
        with self.assertRaises(VideoTaskError):
            create_video_task(
                task_id="video-002", url="https://youtu.be/abcdefghijk",
                submitted_by="owner", created_at="2026-11-13T22:00:00Z",
                agent_ids=("one-agent",),
            )

    def test_report_is_incomplete_until_all_agents_finish(self):
        task = self.make_task()
        report = build_video_report(task)
        self.assertEqual(report["report_status"], "incomplete")
        self.assertFalse(report["view_count_generation"])

    def test_artificial_views_cannot_be_enabled(self):
        task = self.make_task()
        task["artificial_views_allowed"] = True
        self.assertTrue(any("vues artificielles" in error for error in validate_video_task(task)))

    def test_report_ready_after_ten_observations(self):
        task = self.make_task()
        for agent in task["agents"]:
            agent["status"] = "completed"
            agent["observation"] = "Résumé et points clés."
        report = build_video_report(task)
        self.assertEqual(report["agents_completed"], 10)
        self.assertEqual(report["report_status"], "ready_for_consolidation")


class VideoTaskRegistryTests(unittest.TestCase):
    def test_empty_registry_is_valid(self):
        self.assertEqual(validate_video_task_registry({
            "project": "PAPI COMMERCE AI", "schema_version": "1.0", "tasks": [], "note": "empty"
        }), [])

    def test_duplicate_video_task_ids_are_rejected(self):
        task = create_video_task(
            task_id="video-001", url="https://youtu.be/abcdefghijk",
            submitted_by="owner", created_at="2026-11-13T22:00:00Z"
        )
        data = {"project": "PAPI COMMERCE AI", "tasks": [task, dict(task)]}
        self.assertTrue(any("dupliqué" in error for error in validate_video_task_registry(data)))


if __name__ == "__main__":
    unittest.main()
