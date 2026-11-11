"""Compose editable SVG panels on a checked, variable-span grid."""
from copy import deepcopy
import math
import re
import xml.etree.ElementTree as ET

SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a finite positive number')
    return float(value)


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _rewrite_ids(root, prefix):
    ids = {el.attrib['id']: prefix + el.attrib['id'] for el in root.iter() if 'id' in el.attrib}
    for el in root.iter():
        if 'id' in el.attrib:
            el.attrib['id'] = ids[el.attrib['id']]
        for key, val in list(el.attrib.items()):
            for old, new in ids.items():
                val = val.replace(f'url(#{old})', f'url(#{new})')
                if val == '#' + old:
                    val = '#' + new
            el.attrib[key] = val
        if el.tag.endswith('style') and el.text:
            for old, new in ids.items():
                el.text = el.text.replace(f'url(#{old})', f'url(#{new})')
    return root


def compose_svg(spec, render_panel):
    """Return (SVG, layout manifest); render_panel accepts a panel entry."""
    width = _positive(spec.get('width', 1600), 'width')
    height = _positive(spec.get('height', 1100), 'height')
    layout = spec.get('layout', {})
    rows = _integer(layout.get('rows', 1), 'layout.rows', 1)
    cols = _integer(layout.get('cols', 2), 'layout.cols', 1)
    gap = float(layout.get('gap', 24))
    margin = float(layout.get('margin', 28))
    label_h = float(layout.get('label_height', 27))
    header = float(layout.get('header', 65 if spec.get('title') else 15))
    if not all(math.isfinite(x) and x >= 0 for x in (gap, margin, label_h, header)):
        raise ValueError('layout gap/margin/header/label_height must be finite and non-negative')
    cw = layout.get('column_weights', [1] * cols)
    rh = layout.get('row_weights', [1] * rows)
    if len(cw) != cols or len(rh) != rows:
        raise ValueError('grid weight counts must match rows and cols')
    cw = [_positive(x, 'column weight') for x in cw]
    rh = [_positive(x, 'row weight') for x in rh]
    available_w = width - 2 * margin - (cols - 1) * gap
    available_h = height - 2 * margin - header - (rows - 1) * gap
    if min(available_w, available_h) <= 0:
        raise ValueError('canvas is too small for margins and gutters')
    widths = [available_w * x / sum(cw) for x in cw]
    heights = [available_h * x / sum(rh) for x in rh]
    panels = spec.get('panels', [])
    if not panels:
        raise ValueError('multipanel requires at least one panel')
    root = ET.Element(f'{{{SVG}}}svg', width=str(width), height=str(height), viewBox=f'0 0 {width} {height}')
    ET.SubElement(root, f'{{{SVG}}}rect', width='100%', height='100%', fill='white')
    if spec.get('title'):
        el = ET.SubElement(root, f'{{{SVG}}}text', x=str(margin), y=str(margin + 25), fill='#172b3b', attrib={'font-family': 'Arial, sans-serif', 'font-size': '26', 'font-weight': 'bold'})
        el.text = str(spec['title'])
    cells, ids, manifest = set(), set(), []
    for index, panel in enumerate(panels):
        pid = str(panel.get('id', chr(97 + index)))
        if pid in ids:
            raise ValueError(f'duplicate panel id: {pid}')
        ids.add(pid)
        r = _integer(panel.get('row', index // cols), 'panel.row')
        c = _integer(panel.get('col', index % cols), 'panel.col')
        rs = _integer(panel.get('rowspan', 1), 'panel.rowspan', 1)
        cs = _integer(panel.get('colspan', 1), 'panel.colspan', 1)
        if r + rs > rows or c + cs > cols:
            raise ValueError(f'panel {pid} extends outside the grid')
        occupied = {(a, b) for a in range(r, r + rs) for b in range(c, c + cs)}
        if cells & occupied:
            raise ValueError(f'panel {pid} overlaps another panel in the grid')
        cells.update(occupied)
        x = margin + sum(widths[:c]) + c * gap
        y = margin + header + sum(heights[:r]) + r * gap
        w = sum(widths[c:c + cs]) + (cs - 1) * gap
        h = sum(heights[r:r + rs]) + (rs - 1) * gap
        if h <= label_h:
            raise ValueError(f'panel {pid} has no room for content below its label')
        svg = ET.fromstring(render_panel(panel))
        if svg.tag.split('}')[-1] != 'svg':
            raise ValueError(f'panel {pid} did not render an SVG')
        if 'viewBox' not in svg.attrib:
            raise ValueError(f'panel {pid} SVG needs a viewBox')
        source_box = [float(v) for v in re.split(r'[ ,]+', svg.attrib['viewBox'].strip())]
        if len(source_box) != 4 or source_box[2] <= 0 or source_box[3] <= 0:
            raise ValueError(f'panel {pid} has an invalid source viewBox')
        svg = _rewrite_ids(deepcopy(svg), f'p{index}_')
        label = ET.SubElement(root, f'{{{SVG}}}text', x=str(x), y=str(y + 19), fill='#172b3b', attrib={'font-family': 'Arial, sans-serif', 'font-size': '19', 'font-weight': 'bold'})
        label.text = f'({pid})' + (' ' + str(panel['label']) if panel.get('label') else '')
        scale = min(w / source_box[2], (h - label_h) / source_box[3])
        drawn_w, drawn_h = source_box[2] * scale, source_box[3] * scale
        drawn_x = x + (w - drawn_w) / 2
        drawn_y = y + label_h + (h - label_h - drawn_h) / 2
        # Use explicit affine transforms: some PDF exporters ignore nested SVG
        # viewport x/y and preserveAspectRatio. Keep all child objects editable.
        defs = ET.SubElement(root, f'{{{SVG}}}defs')
        clip_id = f'composition_panel_{index}_viewport'
        clip = ET.SubElement(defs, f'{{{SVG}}}clipPath', id=clip_id, clipPathUnits='userSpaceOnUse')
        ET.SubElement(clip, f'{{{SVG}}}rect', x=str(drawn_x), y=str(drawn_y), width=str(drawn_w), height=str(drawn_h))
        outer = ET.SubElement(root, f'{{{SVG}}}g', attrib={'clip-path': f'url(#{clip_id})'})
        tx, ty = drawn_x - source_box[0] * scale, drawn_y - source_box[1] * scale
        inherited = {k: v for k, v in svg.attrib.items() if k not in {'x', 'y', 'width', 'height', 'viewBox', 'preserveAspectRatio', 'version'}}
        inherited['transform'] = f'translate({tx} {ty}) scale({scale})'
        group = ET.SubElement(outer, f'{{{SVG}}}g', attrib=inherited)
        for element in svg.iter():
            # Percent-sized background rectangles refer to the child viewport.
            if element.tag == f'{{{SVG}}}rect':
                for attr, dimension in [('width', source_box[2]), ('height', source_box[3])]:
                    if element.get(attr, '').endswith('%'):
                        element.set(attr, str(float(element.get(attr)[:-1]) * dimension / 100))
        group.extend(list(svg))
        manifest.append({'id': pid, 'row': r, 'col': c, 'rowspan': rs, 'colspan': cs,
                         'slot': [x, y, w, h], 'content_slot': [x, y + label_h, w, h - label_h],
                         'source_viewbox': source_box, 'scale': scale, 'rendered_bounds': [drawn_x, drawn_y, drawn_w, drawn_h],
                         'role': panel.get('role', ''), 'type': panel.get('spec', {}).get('type', '')})
    return ET.tostring(root, encoding='unicode'), {'width': width, 'height': height, 'panels': manifest,
        'checks': {'grid_overlap': 'passed', 'grid_bounds': 'passed'},
        'note': 'Slot geometry is verified; final plot-area alignment and label readability require visual review.'}
