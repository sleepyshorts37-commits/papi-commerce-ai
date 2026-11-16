"""Tests unitaires du socle ONE PROMPT."""
import tempfile
import unittest
from pathlib import Path
from papi_core.publishing import BookProjectError, BookProjectStore, create_book_project, get_project_summary, interpret_brief, validate_project

class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = BookProjectStore(Path(self.tmp.name))
    def tearDown(self):
        self.tmp.cleanup()
    def test_one_prompt_creates_complete_plan_without_execution(self):
        project = create_book_project("Crée une histoire illustrée pour enfants de 6 à 9 ans sur Nia et une rivière magique.", store=self.store)
        self.assertEqual(project["brief"]["age_range"], "6-9")
        self.assertEqual(len(project["tasks"]), 13)
        self.assertFalse(project["execution_enabled"])
        self.assertTrue(project["publication_approval_required"])
        validate_project(project)
    def test_same_prompt_is_idempotent(self):
        prompt = "Un album illustré sur une tortue courageuse."
        first = create_book_project(prompt, store=self.store)
        second = create_book_project(prompt, store=self.store)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(list(Path(self.tmp.name).glob("*.json"))), 1)
    def test_empty_prompt_rejected(self):
        with self.assertRaises(BookProjectError):
            create_book_project("  ", store=self.store)
    def test_summary_reports_planned_not_completed(self):
        project = create_book_project("Un conte pour enfants.", store=self.store)
        summary = get_project_summary(project)
        self.assertEqual(summary["status"], "planned")
        self.assertEqual(summary["planned_tasks"], 13)
    def test_dependencies_reference_existing_tasks(self):
        project = create_book_project("A story for children.", store=self.store)
        ids = {task["id"] for task in project["tasks"]}
        self.assertTrue(all(set(task["dependencies"]).issubset(ids) for task in project["tasks"]))
    def test_brief_marks_defaults(self):
        brief = interpret_brief("Write a story for children.")
        self.assertEqual(brief["language"], "fr")
        self.assertIn("language", brief["assumptions"])

if __name__ == "__main__":
    unittest.main()
