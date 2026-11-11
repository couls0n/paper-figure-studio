"""Behavioral dispatch checks; these do not measure free-text understanding."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from route import route, TYPES


class IntentRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((ROOT / 'assets/routing_cases.json').read_text())['cases']

    def test_reviewed_semantic_cases(self):
        for case in self.cases:
            with self.subTest(case=case['id']):
                result = route(case['intent'])
                expected = case['expected']
                self.assertEqual(result['primary_type'], expected['primary_type'])
                self.assertEqual(result['needs_clarification'], expected['needs_clarification'])
                if 'panel_types' in expected:
                    self.assertEqual([p['primary_type'] for p in result['panel_routes']], expected['panel_types'])

    def test_all_twelve_families_have_a_successful_route(self):
        routed = {route(c['intent'])['primary_type'] for c in self.cases if not c['expected']['needs_clarification']}
        self.assertTrue(set(TYPES).issubset(routed))

    def test_missing_data_does_not_change_type_or_request_route_clarification(self):
        base = {'purpose':'show_change', 'relationship':'ordered_numeric', 'evidence':'ordered_values'}
        results = [route({**base, 'data_status':s}) for s in ['ready', 'partial', 'missing']]
        self.assertEqual([r['primary_type'] for r in results], ['line'] * 3)
        self.assertEqual([r['needs_clarification'] for r in results], [False] * 3)
        self.assertTrue(results[0]['render_ready'])
        self.assertFalse(results[1]['render_ready'])
        self.assertFalse(results[2]['render_ready'])
        self.assertTrue(results[2]['missing_inputs'])

    def test_declared_missing_input_blocks_render_even_if_ready_flag_is_set(self):
        result = route({'explicit_type':'matrix', 'data_status':'ready', 'missing_inputs':['row labels']})
        self.assertEqual(result['primary_type'], 'matrix')
        self.assertEqual(result['status'], 'needs_inputs')
        self.assertFalse(result['render_ready'])

    def test_original_words_do_not_override_semantic_or_negation_fields(self):
        result = route({'request':'不要雷达图，做柱状图。Radar radar radar.', 'purpose':'compare_profiles',
                        'relationship':'profile', 'evidence':'metric_profiles', 'explicit_type':'bar',
                        'excluded_types':['radar'], 'data_status':'ready'})
        self.assertEqual(result['primary_type'], 'bar')

    def test_unparsed_natural_language_is_not_misrepresented_as_classified(self):
        result = route({'request':'Please make a heatmap from these values.'})
        self.assertTrue(result['needs_clarification'])
        self.assertIsNone(result['primary_type'])

    def test_actual_trace_is_distinct_from_numeric_trend_and_system_design(self):
        trace = route({'purpose':'show_execution','relationship':'event_sequence','evidence':'step_records'})
        trend = route({'purpose':'show_change','relationship':'ordered_numeric','evidence':'ordered_values'})
        system = route({'purpose':'explain_system','relationship':'directed_flow','evidence':'nodes_edges'})
        self.assertEqual([trace['primary_type'], trend['primary_type'], system['primary_type']], ['trajectory','line','architecture'])

    def test_independent_rings_not_misrouted_to_taxonomy(self):
        result = route({'purpose':'show_composition','relationship':'part_to_whole','evidence':'counts',
                        'semantic_notes':['two independent marginal distributions']})
        self.assertEqual(result['primary_type'], 'proportion')

    def test_field_mapping_not_misrouted_to_flow(self):
        result = route({'purpose':'organize_categories','relationship':'category_mapping','evidence':'category_mapping'})
        self.assertEqual(result['primary_type'], 'taxonomy')

    def test_nested_layout_routes_each_leaf_and_preserves_missing_input_identity(self):
        result = route({'composition':True,'panels':[
            {'id':'a','intent':{'explicit_type':'architecture','data_status':'ready'}},
            {'id':'b','intent':{'explicit_type':'scatter','data_status':'partial','missing_inputs':['pair IDs']}}
        ]})
        self.assertEqual(result['primary_type'],'multipanel')
        self.assertEqual([p['primary_type'] for p in result['panel_routes']],['architecture','scatter'])
        self.assertEqual(result['missing_inputs'],['b: pair IDs'])
        self.assertFalse(result['render_ready'])
        self.assertFalse(result['needs_clarification'])

    def test_twenty_eight_panels_are_not_silently_truncated(self):
        panels = [{'id':f'{row}-{col}', 'intent':{'explicit_type':'scatter','data_status':'ready'}}
                  for row in range(7) for col in range(4)]
        result = route({'composition':True,'panels':panels})
        self.assertEqual(len(result['panel_routes']),28)
        self.assertEqual({p['id'] for p in result['panel_routes']},{p['id'] for p in panels})
        self.assertTrue(result['render_ready'])

    def test_missing_shared_inputs_are_preserved(self):
        result=route({'composition':True,'missing_inputs':['shared legend mapping'],'panels':[
            {'id':'a','intent':{'explicit_type':'bar','data_status':'ready'}},
            {'id':'b','intent':{'explicit_type':'line','data_status':'ready'}}]})
        self.assertEqual(result['missing_inputs'],['shared legend mapping'])
        self.assertFalse(result['render_ready'])
        self.assertEqual(result['reference'],'references/composition.md')

    def test_parent_exclusion_applies_to_all_panels(self):
        result=route({'composition':True,'excluded_types':['proportion'],'panels':[
            {'id':'a','intent':{'purpose':'show_composition','relationship':'part_to_whole','evidence':'counts','data_status':'ready'}},
            {'id':'b','intent':{'explicit_type':'line','data_status':'ready'}}
        ]})
        self.assertEqual(result['panel_routes'][0]['primary_type'],'bar')
        self.assertEqual(result['panel_routes'][1]['primary_type'],'line')

    def test_input_is_not_mutated(self):
        original={'composition':True,'excluded_types':['proportion'],'panels':[
            {'id':'a','intent':{'explicit_type':'bar'}}, {'id':'b','intent':{'explicit_type':'line'}}]}
        before=copy.deepcopy(original)
        route(original)
        self.assertEqual(before,original)

    def test_invalid_schema_and_duplicate_panels_fail_loudly(self):
        invalid=[{'purpose':'analyse_everything'}, {'explicit_type':'heatmap'}, {'data_status':'faked'},
                 {'excluded_types':'bar'}, {'composition':'yes'}, {'schema_version':True},
                 {'purpsoe':'compare_values'}, {'panels':[{'id':'a','intent':{}},{'id':'a','intent':{}}]}]
        for intent in invalid:
            with self.subTest(intent=intent), self.assertRaises(ValueError):
                route(intent)

    def test_nested_multipanel_is_rejected_instead_of_lost(self):
        with self.assertRaises(ValueError):
            route({'composition':True,'panels':[
                {'id':'a','intent':{'composition':True,'panels':[{'id':'x','intent':{}},{'id':'y','intent':{}}]}},
                {'id':'b','intent':{'explicit_type':'line'}}]})

    def test_schema_accepts_reviewed_fixtures(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema is an optional test dependency')
        schema=json.loads((ROOT/'references/intent.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        validator=jsonschema.Draft202012Validator(schema)
        for case in self.cases:
            with self.subTest(case=case['id']):
                validator.validate(case['intent'])

    def test_cli_stdin_and_exit_codes(self):
        for intent,code in [({'explicit_type':'bar','data_status':'missing'},0), ({'request':'Make a figure'},3), ({'explicit_type':'not-a-type'},2)]:
            with self.subTest(intent=intent):
                p=subprocess.run([sys.executable,str(ROOT/'scripts/route.py')],input=json.dumps(intent),text=True,capture_output=True)
                self.assertEqual(p.returncode,code)
                data=json.loads(p.stderr if code==2 else p.stdout)
                self.assertIsInstance(data,dict)


if __name__=='__main__':
    unittest.main()
