import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from route import route
from schematics import render_schematic


class StyleRoutingTests(unittest.TestCase):
    def test_each_priority_panel_keeps_its_own_profile(self):
        intent = {'composition': True, 'panels': [
            {'id': 'case', 'intent': {'purpose': 'compare_cases', 'relationship': 'qualitative_contrast', 'data_status': 'ready'}},
            {'id': 'method', 'intent': {'purpose': 'explain_system', 'relationship': 'directed_flow', 'data_status': 'ready'}},
            {'id': 'run', 'intent': {'purpose': 'show_execution', 'relationship': 'event_sequence', 'data_status': 'ready'}}]}
        result = route(intent)
        self.assertEqual(result['primary_type'], 'multipanel')
        self.assertEqual([p['style_profile'] for p in result['panel_routes']], ['paper_case', 'paper_flow', 'paper_trace'])
        self.assertEqual([p['primary_type'] for p in result['panel_routes']], ['comparison', 'architecture', 'trajectory'])

    def test_missing_evidence_keeps_style_but_does_not_allow_render(self):
        result = route({'purpose': 'show_execution', 'relationship': 'event_sequence', 'evidence': 'screenshots', 'data_status': 'missing'})
        self.assertEqual(result['style_profile'], 'paper_trace')
        self.assertFalse(result['render_ready'])
        self.assertTrue(result['missing_inputs'])
        ambiguous = route({'request': 'Compare these things', 'purpose': 'unknown', 'evidence': 'unknown'})
        self.assertTrue(ambiguous['needs_clarification'])
        self.assertNotIn('style_profile', ambiguous)

    def test_aesthetic_profile_cannot_silently_change_semantic_family(self):
        with self.assertRaisesRegex(ValueError, 'belongs to comparison'):
            render_schematic({'type': 'architecture', 'data': {}, 'style': {'profile': 'paper_case'}})
        with self.assertRaisesRegex(ValueError, 'Unknown schematic style.profile'):
            render_schematic({'type': 'comparison', 'data': {}, 'style': {'profile': 'unknown'}})


if __name__ == '__main__':
    unittest.main()
