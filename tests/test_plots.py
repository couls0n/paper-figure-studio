import copy
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from plots import render_plot, validate_plot, _draw_line, _draw_matrix, _draw_scatter, _kde
import matplotlib.pyplot as plt
import numpy as np


def template(name):
    return json.loads((ROOT / 'assets' / 'templates' / f'{name}.json').read_text())


class PlotContracts(unittest.TestCase):
    def test_every_family_renders_editable_svg_at_requested_size(self):
        for typ in ['proportion', 'bar', 'line', 'matrix', 'scatter', 'distribution', 'radar']:
            with self.subTest(type=typ):
                spec = template(typ)
                spec['width'], spec['height'] = 900, 600
                root = ET.fromstring(render_plot(spec))
                self.assertEqual(root.attrib['viewBox'], '0 0 900 600')
                self.assertEqual(root.attrib['width'], '900')
                self.assertGreater(len(root.findall('.//{http://www.w3.org/2000/svg}text')), 5)
                self.assertIn('ILLUSTRATIVE DATA', ''.join(root.itertext()))

    def test_category_labels_survive_final_axis_decoration(self):
        spec = template("bar")
        svg = render_plot(spec)
        labels = " ".join(ET.fromstring(svg).itertext())
        for category in spec["data"]["categories"]:
            self.assertIn(category, labels)

    def test_numeric_line_keeps_distances_and_missing_point_gap(self):
        data = template('line')['data']
        data['series'][0].pop('lower')
        data['series'][0].pop('upper')
        data['series'][0]['y'][1] = None
        fig, ax = plt.subplots()
        try:
            _draw_line(ax, data)
            self.assertEqual(list(ax.lines[0].get_xdata()), [15, 30, 60])
            self.assertTrue(np.isnan(ax.lines[0].get_ydata()[1]))
            self.assertEqual(ax.lines[0].get_xdata()[2]-ax.lines[0].get_xdata()[1], 30)
        finally:
            plt.close(fig)

    def test_zero_and_mask_are_distinct_matrix_cells(self):
        data = {'values': [[0, 7], [2, 0]], 'row_labels': ['A', 'B'], 'column_labels': ['A', 'B'], 'mask': [[True, False], [False, False]], 'format': '.0f'}
        fig, ax = plt.subplots()
        try:
            _draw_matrix(fig, ax, data)
            self.assertEqual([t.get_text() for t in ax.texts], ['—', '7', '2', '0'])
            mask = np.ma.getmaskarray(ax.collections[0].get_array())
            self.assertTrue(mask[0, 0])
            self.assertFalse(mask[1, 1])
        finally:
            plt.close(fig)

    def test_independent_ring_totals_are_each_validated(self):
        spec = template('proportion')
        validate_plot(spec)
        spec['data']['rings'][1]['values'] = [50, 30, 10]
        with self.assertRaisesRegex(ValueError, 'total 100'):
            validate_plot(spec)

    def test_pair_endpoints_resolve_to_named_observations(self):
        spec = template('scatter')
        data = spec['data']
        fig, ax = plt.subplots()
        try:
            _draw_scatter(ax, data)
            arrows = [t for t in ax.texts if t.arrow_patch is not None]
            self.assertEqual(tuple(arrows[0].xy), (69, 11))
            self.assertEqual(tuple(arrows[0].xyann), (72, 35))
        finally:
            plt.close(fig)
        data['pairs'][0]['to_id'] = 'does-not-exist'
        with self.assertRaisesRegex(ValueError, 'existing point_id'):
            validate_plot(spec)

    def test_radar_rejects_mixed_axis_order_or_range(self):
        spec = template('radar')
        spec['data']['series'][1]['axes'] = list(reversed(spec['data']['axes']))
        with self.assertRaisesRegex(ValueError, 'same axis order'):
            validate_plot(spec)
        spec = template('radar')
        spec['data']['series'][0]['values'][1] = 105
        with self.assertRaisesRegex(ValueError, 'shared range'):
            validate_plot(spec)

    def test_uncertainty_cannot_be_unlabelled_or_reversed(self):
        spec = template('bar')
        del spec['data']['uncertainty']
        with self.assertRaisesRegex(ValueError, 'uncertainty'):
            validate_plot(spec)
        spec = template('line')
        spec['data']['series'][0]['lower'][0] = 90
        with self.assertRaisesRegex(ValueError, 'lower <= y <= upper'):
            validate_plot(spec)

    def test_kde_integrates_to_one_without_synthetic_observations(self):
        samples = np.array([-2, -1, -.3, 0, .4, 1, 2])
        grid = np.linspace(-10, 10, 2000)
        density = _kde(samples, grid, .5)
        self.assertAlmostEqual(float(np.trapezoid(density, grid)), 1, places=5)
        self.assertTrue(np.all(density >= 0))

    def test_nonfinite_or_dimension_mismatch_is_rejected(self):
        spec = template('bar')
        spec['data']['series'][0]['values'][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite'):
            validate_plot(spec)
        spec = template('matrix')
        spec['data']['values'][1].append(9)
        with self.assertRaisesRegex(ValueError, 'expected 3'):
            validate_plot(spec)

    def test_nonzero_bar_baseline_is_explicit(self):
        spec = template('bar')
        spec['data']['y_range'] = [50, 100]
        with self.assertRaisesRegex(ValueError, 'truncated bar baseline'):
            validate_plot(spec)
        spec['data']['allow_truncated_baseline'] = True
        spec['data']['baseline_note'] = 'Faithful reproduction: source used a 50% baseline.'
        validate_plot(spec)


if __name__ == '__main__':
    unittest.main()
