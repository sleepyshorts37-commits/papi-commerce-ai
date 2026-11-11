import unittest

from papi_core.organization import (
    OrganizationError, build_organization, get_team, organization_summary,
)


class OrganizationTests(unittest.TestCase):
    def setUp(self):
        self.agents = [
            {"id": "marietou", "name": "Marietou", "department": "Direction",
             "status": "defined", "manager_agent_id": "president"},
            {"id": "astou", "name": "Astou", "department": "Direction",
             "status": "defined", "manager_agent_id": "marietou"},
            {"id": "seydina", "name": "Seydina", "department": "Recherche",
             "status": "planned", "manager_agent_id": "astou"},
            {"id": "mariama", "name": "Mariama", "department": "Qualité",
             "status": "planned", "manager_agent_id": "marietou"},
        ]

    def test_builds_hierarchy_and_direct_or_recursive_teams(self):
        org = build_organization(self.agents)
        self.assertEqual(org["total_agents"], 4)
        self.assertEqual(get_team(org, "marietou"), ["astou", "mariama"])
        self.assertEqual(get_team(org, "marietou", recursive=True),
                         ["astou", "mariama", "seydina"])
        self.assertEqual(get_team(org, "president"), ["marietou"])

    def test_rejects_duplicate_ids_case_insensitively(self):
        agents = self.agents + [{**self.agents[0], "id": "MARIETOU"}]
        with self.assertRaises(OrganizationError):
            build_organization(agents)

    def test_rejects_unknown_manager_and_self_management(self):
        for changed in (
            [{**self.agents[0], "manager_agent_id": "missing"}],
            [{**self.agents[0], "manager_agent_id": "marietou"}],
        ):
            with self.assertRaises(OrganizationError):
                build_organization(changed)

    def test_rejects_hierarchical_cycles(self):
        agents = [
            {"id": "a", "manager_agent_id": "b"},
            {"id": "b", "manager_agent_id": "a"},
        ]
        with self.assertRaises(OrganizationError):
            build_organization(agents)

    def test_summary_distinguishes_defined_planned_and_active(self):
        summary = organization_summary(build_organization(self.agents))
        self.assertEqual(summary["total_agents"], 4)
        self.assertEqual(summary["active_agents"], 0)
        self.assertEqual(summary["statuses"], {"defined": 2, "planned": 2})


if __name__ == "__main__":
    unittest.main()
