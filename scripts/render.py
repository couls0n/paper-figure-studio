#!/usr/bin/env python3
"""Render a figure specification to editable SVG plus optional PDF/PNG."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

SCHEMATIC_TYPES = {'architecture', 'comparison', 'trajectory', 'text_card', 'taxonomy'}
PLOT_TYPES = {'proportion', 'bar', 'line', 'matrix', 'scatter', 'distribution', 'radar'}


def load_spec(path):
    path = Path(path).resolve()
    spec = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(spec, dict):
        raise ValueError('figure spec must be a JSON object')
    spec['_base_dir'] = str(path.parent)
    return spec


def render_spec(spec, depth=0):
    if depth > 6:
        raise ValueError('multipanel nesting exceeds 6 levels (possible recursive spec_file)')
    if not isinstance(spec, dict):
        raise ValueError('each figure specification must be an object')
    kind = spec.get('type')
    if spec.get('data_status') not in {'observed', 'transcribed', 'digitized', 'illustrative'}:
        raise ValueError('data_status must be observed, transcribed, digitized, or illustrative')
    if kind in SCHEMATIC_TYPES:
        from schematics import render_schematic
        svg = render_schematic(spec)
        return svg, None
    if kind in PLOT_TYPES:
        from plots import render_plot
        svg = render_plot(spec)
        return svg, None
    if kind == 'multipanel':
        from compose import compose_svg
        base = Path(spec.get('_base_dir', '.'))
        rendered_types = []
        def child(panel):
            if bool(panel.get('spec_file')) == bool(panel.get('spec')):
                raise ValueError('each panel requires exactly one of spec or spec_file')
            if panel.get('spec_file'):
                p = load_spec(base / panel['spec_file'])
            else:
                p = deepcopy(panel['spec'])
                p.setdefault('_base_dir', str(base))
            # Inline panel data inherits the parent declaration unless explicitly set.
            p.setdefault('data_status', spec['data_status'])
            svg, _ = render_spec(p, depth + 1)
            rendered_types.append(p['type'])
            return svg
        svg, manifest = compose_svg(spec, child)
        for panel, panel_type in zip(manifest['panels'], rendered_types):
            panel['type'] = panel_type
        return svg, manifest
    raise ValueError(f'unknown type {kind!r}; choose one of {sorted(SCHEMATIC_TYPES | PLOT_TYPES | {"multipanel"})}')


def export(spec, out, formats=('svg', 'png', 'pdf'), scale=2):
    if not set(formats) <= {'svg', 'png', 'pdf'}:
        raise ValueError('formats may only contain svg,png,pdf')
    if not 0 < scale <= 8:
        raise ValueError('PNG scale must be between 0 and 8')
    svg, layout = render_spec(spec)
    root = ET.fromstring(svg)
    if root.tag.split('}')[-1] != 'svg' or 'viewBox' not in root.attrib:
        raise ValueError('renderer produced an invalid SVG root')
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    outputs = []
    # Always keep the editable SVG even if only raster/PDF was requested.
    svg_path = out.with_suffix('.svg')
    svg_path.write_text(svg, encoding='utf-8')
    outputs.append(str(svg_path))
    if 'png' in formats or 'pdf' in formats:
        import pymupdf
        doc = pymupdf.open(stream=svg.encode(), filetype='svg')
        pdf_data = doc.convert_to_pdf()
        pdf = pymupdf.open(stream=pdf_data, filetype='pdf')
        if 'pdf' in formats:
            path = out.with_suffix('.pdf')
            path.write_bytes(pdf_data)
            outputs.append(str(path))
        if 'png' in formats:
            path = out.with_suffix('.png')
            pdf[0].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).save(path)
            outputs.append(str(path))
        pdf.close()
        doc.close()
    metadata = {'type': spec['type'], 'data_status': spec['data_status'], 'title': spec.get('title', ''),
                'outputs': outputs, 'editable_source': str(svg_path), 'layout': layout,
                'style_profile': spec.get('style', {}).get('profile'),
                'style_reference': spec.get('style_reference'),
                'visual_review_required': True}
    out.with_suffix('.render.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', help='JSON specification; image/spec_file paths are relative to it')
    parser.add_argument('--out', required=True, help='output prefix, without a suffix')
    parser.add_argument('--formats', default='svg,png,pdf')
    parser.add_argument('--scale', type=float, default=2, help='PNG scaling factor (default 2)')
    args = parser.parse_args()
    try:
        result = export(load_spec(args.spec), args.out, tuple(args.formats.split(',')), args.scale)
    except (ValueError, KeyError, OSError, TypeError, ET.ParseError) as error:
        print(f'Figure error: {error}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
