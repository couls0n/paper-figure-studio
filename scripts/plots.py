"""Editable quantitative SVGs for seven paper-figure families.

The input data are authoritative.  No sample generation, digitisation or inferred
uncertainty occurs here.  Templates explicitly identify their data as illustrative.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

PLOT_TYPES = frozenset({"proportion", "bar", "line", "matrix", "scatter", "distribution", "radar"})
PALETTE = ["#246C91", "#D68443", "#4E927B", "#8D6AA8", "#C65D6D", "#7D8793", "#B19B46", "#5D9DA8"]
SVG = "http://www.w3.org/2000/svg"


def _error(message):
    raise ValueError(message)


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _error(f"{field} must be a finite number, got {value!r}")
    return float(value)


def _numbers(values, field, length=None, allow_null=False):
    if not isinstance(values, list) or not values:
        _error(f"{field} must be a non-empty array")
    if length is not None and len(values) != length:
        _error(f"{field} has {len(values)} values; expected {length}")
    return np.array([np.nan if v is None and allow_null else _number(v, f"{field}[{i}]") for i, v in enumerate(values)], dtype=float)


def _labels(values, field, length=None, unique=False):
    if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
        _error(f"{field} must contain non-empty strings")
    if length is not None and len(values) != length:
        _error(f"{field} has {len(values)} entries; expected {length}")
    if unique and len(set(values)) != len(values):
        _error(f"{field} must be unique")
    return values


def _series(data):
    s = data.get("series")
    if not isinstance(s, list) or not s:
        _error("data.series must be a non-empty array")
    _labels([v.get("name") for v in s], "series names", unique=True)
    return s


def _uncertainty(data):
    if not isinstance(data.get("uncertainty"), str) or not data["uncertainty"].strip():
        _error("Error bars or bands require data.uncertainty, e.g. '95% bootstrap CI across 20 seeds'")


def _axis_limits(data, name):
    lim = data.get(name)
    if lim is None:
        return None
    vals = _numbers(lim, f"data.{name}", 2)
    if vals[0] >= vals[1]:
        _error(f"data.{name} must be [min, max] with min < max")
    return vals


def _font_family():
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC", "Arial Unicode MS", "Microsoft YaHei"):
        if name in available:
            return ["DejaVu Sans", name]
    return ["DejaVu Sans"]


def validate_plot(spec):
    """Validate the public spec without drawing; returns a detached copy."""
    if not isinstance(spec, dict) or spec.get("type") not in PLOT_TYPES:
        _error("Unknown plot type; expected one of " + ", ".join(sorted(PLOT_TYPES)))
    for key, default in (("width", 1000), ("height", 650)):
        value = _number(spec.get(key, default), key)
        if value < 320 or value > 10000:
            _error(f"{key} must be between 320 and 10000 px")
    if not isinstance(spec.get("data"), dict):
        _error("data must be an object")
    if spec.get("data_status") not in {"illustrative", "observed", "transcribed", "digitized"}:
        _error("data_status must be illustrative, observed, transcribed or digitized")
    d = spec["data"]
    typ = spec["type"]
    for name in ("x_range", "y_range"):
        _axis_limits(d, name)
    if typ == "proportion":
        rings = d.get("rings")
        if not isinstance(rings, list) or not rings or len(rings) > 5:
            _error("data.rings must contain 1 to 5 independent distributions")
        if d.get("layout", "concentric") not in {"concentric", "side_by_side"}:
            _error("proportion layout must be concentric or side_by_side")
        for i, r in enumerate(rings):
            labels = _labels(r.get("labels"), f"rings[{i}].labels", unique=True)
            vals = _numbers(r.get("values"), f"rings[{i}].values", len(labels))
            if np.any(vals < 0) or vals.sum() <= 0:
                _error("Each distribution requires non-negative values and a positive total")
            if r.get("unit") == "percent" and not np.isclose(vals.sum(), 100, atol=0.11):
                _error("A percent distribution must total 100 (rounding tolerance 0.11)")
            if r.get("denominator") is not None and _number(r["denominator"], "denominator") <= 0:
                _error("denominator must be positive")
    elif typ == "bar":
        cats = _labels(d.get("categories"), "data.categories", unique=True)
        if d.get("orientation", "vertical") not in {"vertical", "horizontal"}:
            _error("bar orientation must be vertical or horizontal")
        for i, s in enumerate(_series(d)):
            _numbers(s.get("values"), f"series[{i}].values", len(cats), allow_null=True)
            if "errors" in s:
                errs = _numbers(s["errors"], f"series[{i}].errors", len(cats))
                if np.any(errs < 0):
                    _error("errors must be non-negative half-widths")
                _uncertainty(d)
        limit = _axis_limits(d, "x_range" if d.get("orientation") == "horizontal" else "y_range")
        if limit is not None and not (limit[0] <= 0 <= limit[1]) and not d.get("allow_truncated_baseline", False):
            _error("A truncated bar baseline requires allow_truncated_baseline=true and an explanatory note")
        if d.get("allow_truncated_baseline") and not d.get("baseline_note"):
            _error("A truncated baseline requires data.baseline_note")
    elif typ == "line":
        x = d.get("x")
        if d.get("x_kind", "numeric") == "categorical":
            _labels(x, "data.x", unique=True)
        elif d.get("x_kind", "numeric") == "numeric":
            xx = _numbers(x, "data.x")
            if len(xx) > 1 and np.any(np.diff(xx) <= 0):
                _error("Numeric x must be strictly increasing; sort x and all matching series together")
        else:
            _error("x_kind must be numeric or categorical")
        for i, s in enumerate(_series(d)):
            yy = _numbers(s.get("y"), f"series[{i}].y", len(x), allow_null=True)
            if ("lower" in s) != ("upper" in s):
                _error("Uncertainty bands need both lower and upper arrays")
            if "lower" in s:
                lo = _numbers(s["lower"], "lower", len(x), allow_null=True)
                hi = _numbers(s["upper"], "upper", len(x), allow_null=True)
                if np.any(lo > hi) or np.any(lo > yy) or np.any(hi < yy):
                    _error("Bands must satisfy lower <= y <= upper at observed points")
                _uncertainty(d)
    elif typ == "matrix":
        rows = _labels(d.get("row_labels"), "row_labels", unique=True)
        cols = _labels(d.get("column_labels"), "column_labels", unique=True)
        vals = d.get("values")
        if not isinstance(vals, list) or len(vals) != len(rows):
            _error("matrix row count must match row_labels")
        arr = np.array([_numbers(row, f"values[{i}]", len(cols), True) for i, row in enumerate(vals)])
        if not np.isfinite(arr).any():
            _error("matrix needs at least one observed value")
        if "mask" in d:
            mask = d["mask"]
            if not isinstance(mask, list) or len(mask) != len(rows) or any(not isinstance(row, list) or len(row) != len(cols) or any(not isinstance(x, bool) for x in row) for row in mask):
                _error("mask must be a boolean matrix with the same shape as values")
        kind = d.get("kind", "general")
        if kind not in {"general", "transfer", "correlation", "confusion"}:
            _error("matrix kind must be general, transfer, correlation or confusion")
        if kind == "correlation":
            if rows != cols or not np.allclose(arr, arr.T, equal_nan=True) or np.nanmin(arr) < -1 or np.nanmax(arr) > 1:
                _error("Correlation matrices need matching axes, symmetric values and a [-1,1] range")
        if kind == "confusion" and (len(rows) != len(cols) or np.nanmin(arr) < 0):
            _error("Confusion matrices must be square with non-negative counts/rates")
        if "vmin" in d and "vmax" in d and _number(d["vmin"], "vmin") >= _number(d["vmax"], "vmax"):
            _error("vmin must be less than vmax")
    elif typ == "scatter":
        point_ids = set()
        for i, s in enumerate(_series(d)):
            points = s.get("points")
            if not isinstance(points, list) or not points:
                _error("Each scatter series needs a non-empty points array")
            for j, point in enumerate(points):
                _numbers(point, f"series[{i}].points[{j}]", 2)
            if "labels" in s:
                _labels(s["labels"], f"series[{i}].labels", len(points))
            if "point_ids" in s:
                ids = _labels(s["point_ids"], "point_ids", len(points), True)
                if point_ids.intersection(ids):
                    _error("point_ids must be unique across series")
                point_ids.update(ids)
        for pair in d.get("pairs", []):
            if "from_id" in pair or "to_id" in pair:
                if pair.get("from_id") not in point_ids or pair.get("to_id") not in point_ids:
                    _error("Every pair endpoint must reference an existing point_id")
            else:
                _numbers(pair.get("from"), "pair.from", 2)
                _numbers(pair.get("to"), "pair.to", 2)
        for name in ("x_reference", "y_reference"):
            if name in d:
                _number(d[name], name)
    elif typ == "distribution":
        kind = d.get("kind", "histogram")
        if kind not in {"histogram", "kde"}:
            _error("distribution kind must be histogram or kde")
        groups = d.get("groups")
        if not isinstance(groups, list) or not groups:
            _error("data.groups must be a non-empty list of real samples")
        _labels([g.get("name") for g in groups], "group names", unique=True)
        for g in groups:
            vals = _numbers(g.get("samples"), "samples")
            if kind == "kde" and len(vals) < 2:
                _error("KDE requires at least two observations per group")
            if kind == "kde" and np.std(vals) == 0 and d.get("bandwidth") is None:
                _error("Constant samples need an explicit positive KDE bandwidth")
        bins = d.get("bins", 12)
        if isinstance(bins, list):
            arr = _numbers(bins, "bins")
            if len(arr) < 2 or np.any(np.diff(arr) <= 0):
                _error("Bin edges must be strictly increasing")
        elif isinstance(bins, bool) or not isinstance(bins, int) or bins < 1:
            _error("bins must be a positive integer or ordered edges")
        if d.get("bandwidth") is not None and _number(d["bandwidth"], "bandwidth") <= 0:
            _error("KDE bandwidth must be positive")
    elif typ == "radar":
        axes = _labels(d.get("axes"), "data.axes", unique=True)
        if len(axes) < 3:
            _error("A radar chart needs at least three dimensions")
        bounds = _numbers(d.get("range"), "data.range", 2)
        if bounds[0] >= bounds[1]:
            _error("radar range must be increasing")
        for s in _series(d):
            vals = _numbers(s.get("values"), "radar values", len(axes))
            if np.any(vals < bounds[0]) or np.any(vals > bounds[1]):
                _error("Radar values must fit the explicitly shared range")
            if s.get("axes", axes) != axes:
                _error("Every radar series must use exactly the same axis order")
    return copy.deepcopy(spec)


def _decorate(ax, d):
    ax.set_xlabel(d.get("x_label", ""))
    ax.set_ylabel(d.get("y_label", ""))
    for field, fn in (("x_range", ax.set_xlim), ("y_range", ax.set_ylim)):
        if field in d:
            fn(d[field])
    if d.get("x_scale", "linear") not in {"linear", "log", "symlog"} or d.get("y_scale", "linear") not in {"linear", "log", "symlog"}:
        _error("Axis scale must be linear, log or symlog")
    if d.get("x_scale", "linear") != ax.get_xscale():
        ax.set_xscale(d["x_scale"])
    if d.get("y_scale", "linear") != ax.get_yscale():
        ax.set_yscale(d["y_scale"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)


def _draw_bar(ax, d):
    cats = d["categories"]
    ss = d["series"]
    x = np.arange(len(cats), dtype=float)
    span = .78 / len(ss)
    horizontal = d.get("orientation", "vertical") == "horizontal"
    for i, s in enumerate(ss):
        positions = x + (i - (len(ss)-1)/2) * span
        values = np.array([np.nan if v is None else v for v in s["values"]])
        options = dict(label=s["name"], color=PALETTE[i % len(PALETTE)], alpha=.9, capsize=3, error_kw={"elinewidth":1.1})
        if horizontal:
            bars = ax.barh(positions, values, height=span*.9, xerr=s.get("errors"), **options)
        else:
            bars = ax.bar(positions, values, width=span*.9, yerr=s.get("errors"), **options)
        if d.get("annotate", False):
            ax.bar_label(bars, fmt=d.get("format", "%.1f"), padding=4, fontsize=9)
    if horizontal:
        ax.set_yticks(x, cats)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=.22)
    else:
        ax.set_xticks(x, cats, rotation=d.get("label_rotation", 0))
        ax.grid(axis="y", alpha=.22)
    ax.legend(frameon=False, ncol=min(len(ss), 4), loc="best")


def _draw_line(ax, d):
    x = np.arange(len(d["x"])) if d.get("x_kind", "numeric") == "categorical" else np.asarray(d["x"])
    for i, s in enumerate(d["series"]):
        color = PALETTE[i % len(PALETTE)]
        y = np.array([np.nan if v is None else v for v in s["y"]])
        ax.plot(x, y, marker=["o","s","^","D"][i % 4], color=color, linewidth=2, markersize=5, label=s["name"])
        if "lower" in s:
            lo = np.array([np.nan if v is None else v for v in s["lower"]])
            hi = np.array([np.nan if v is None else v for v in s["upper"]])
            ax.fill_between(x, lo, hi, color=color, alpha=.15, linewidth=0)
    if d.get("x_kind", "numeric") == "categorical":
        ax.set_xticks(x, d["x"], rotation=d.get("label_rotation", 0))
    else:
        ax.set_xticks(x)
    if "baseline" in d:
        ax.axhline(_number(d["baseline"], "baseline"), color="#6F7B85", linestyle="--", label=d.get("baseline_label", "Reference"))
    ax.grid(alpha=.22)
    ax.legend(frameon=False, ncol=min(len(d["series"]),3), loc="best")


def _draw_matrix(fig, ax, d):
    values = np.array([[np.nan if v is None else v for v in row] for row in d["values"]])
    mask = np.isnan(values) | np.array(d.get("mask", np.zeros_like(values, dtype=bool)), dtype=bool)
    kind = d.get("kind", "general")
    vmin = d.get("vmin", -1 if kind == "correlation" else float(np.nanmin(values)))
    vmax = d.get("vmax", 1 if kind == "correlation" else float(np.nanmax(values)))
    if vmin == vmax:
        vmax = vmin + 1
    cmap = matplotlib.colormaps[d.get("cmap", "RdBu_r" if kind == "correlation" else "Blues")].with_extremes(bad="#F2F4F6")
    # QuadMesh exports one vector cell per value instead of embedding a bitmap.
    im = ax.pcolormesh(np.arange(values.shape[1]+1)-.5, np.arange(values.shape[0]+1)-.5,
                       np.ma.array(values, mask=mask), cmap=cmap, vmin=vmin, vmax=vmax,
                       shading="flat", edgecolors="white", linewidth=.7)
    ax.set_xlim(-.5, values.shape[1]-.5)
    ax.set_ylim(values.shape[0]-.5, -.5)
    ax.set_xticks(np.arange(values.shape[1]), d["column_labels"], rotation=d.get("label_rotation", 30), ha="right")
    ax.set_yticks(np.arange(values.shape[0]), d["row_labels"])
    if d.get("annotate", True):
        fmt = d.get("format", ".2f")
        for row in range(values.shape[0]):
            for col in range(values.shape[1]):
                if mask[row,col]:
                    label = d.get("mask_label", "—")
                    color = "#6A7680"
                else:
                    label = format(values[row,col], fmt)
                    rgba = cmap(im.norm(values[row,col]))
                    lum = .2126*rgba[0]+.7152*rgba[1]+.0722*rgba[2]
                    color = "#FFFFFF" if lum < .5 else "#162435"
                ax.text(col,row,label,ha="center",va="center",color=color,fontsize=10)
    cb = fig.colorbar(im, ax=ax, shrink=.88, pad=.035)
    cb.set_label(d.get("unit", "Value"))
    ax.set_xlabel(d.get("x_label", "Predicted label" if kind == "confusion" else "Target"))
    ax.set_ylabel(d.get("y_label", "True label" if kind == "confusion" else "Source"))


def _draw_scatter(ax, d):
    ids = {}
    markers = ["o","s","^","D","P","X","v","h"]
    for i,s in enumerate(d["series"]):
        pts = np.array(s["points"])
        ax.scatter(pts[:,0],pts[:,1],s=s.get("size",64),label=s["name"],color=PALETTE[i%len(PALETTE)],marker=markers[i%len(markers)],alpha=s.get("alpha",.9),edgecolors="white",linewidths=.7)
        for j, label in enumerate(s.get("labels",[])):
            ax.annotate(label,pts[j],xytext=(6,6),textcoords="offset points",fontsize=9)
        for pid,point in zip(s.get("point_ids",[]),pts):
            ids[pid]=point
    for pair in d.get("pairs",[]):
        start,end = (ids[pair["from_id"]],ids[pair["to_id"]]) if "from_id" in pair else (pair["from"],pair["to"])
        ax.annotate("",xy=end,xytext=start,arrowprops={"arrowstyle":"->","color":"#5D6974","lw":1.25,"shrinkA":5,"shrinkB":5})
        if pair.get("label"):
            midpoint=(np.asarray(start)+np.asarray(end))/2
            ax.annotate(pair["label"],midpoint,xytext=(0,8),textcoords="offset points",ha="center",fontsize=9)
    if "x_reference" in d:
        ax.axvline(d["x_reference"],color="#8895A1",linestyle="--",linewidth=1)
    if "y_reference" in d:
        ax.axhline(d["y_reference"],color="#8895A1",linestyle="--",linewidth=1)
    if d.get("diagonal"):
        lo,hi = min(ax.get_xlim()[0],ax.get_ylim()[0]),max(ax.get_xlim()[1],ax.get_ylim()[1])
        ax.plot([lo,hi],[lo,hi],color="#8895A1",linestyle="--",linewidth=1)
    ax.grid(alpha=.2)
    ax.legend(frameon=False,loc="best")


def _kde(samples, grid, bandwidth=None):
    """Gaussian KDE, chunked to avoid an n×grid temporary for large samples."""
    samples=np.asarray(samples,dtype=float)
    bw=bandwidth if bandwidth is not None else 1.06*np.std(samples,ddof=1)*len(samples)**(-.2)
    if not math.isfinite(bw) or bw<=0:
        _error("KDE bandwidth is not positive; provide data.bandwidth")
    density=np.zeros_like(grid)
    for start in range(0,len(samples),4096):
        z=(grid[:,None]-samples[None,start:start+4096])/bw
        density+=np.exp(-.5*z*z).sum(axis=1)
    return density/(len(samples)*bw*np.sqrt(2*np.pi))


def _draw_distribution(ax,d):
    groups=d["groups"]
    all_values=np.concatenate([np.array(g["samples"]) for g in groups])
    if d.get("kind","histogram")=="histogram":
        bins=d.get("bins",12)
        bins=np.histogram_bin_edges(all_values,bins=bins) if isinstance(bins,int) else bins
        for i,g in enumerate(groups):
            ax.hist(g["samples"],bins=bins,density=d.get("density",False),alpha=.45,label=g["name"],color=PALETTE[i%len(PALETTE)],edgecolor="white",linewidth=.6)
        ax.set_ylabel(d.get("y_label","Density" if d.get("density") else "Count"))
    else:
        spread=float(np.ptp(all_values)) or 1
        bounds=d.get("x_range",[float(all_values.min()-.15*spread),float(all_values.max()+.15*spread)])
        grid=np.linspace(*bounds,400)
        for i,g in enumerate(groups):
            den=_kde(g["samples"],grid,d.get("bandwidth"))
            ax.plot(grid,den,color=PALETTE[i%len(PALETTE)],label=g["name"],lw=1.8)
            ax.fill_between(grid,den,color=PALETTE[i%len(PALETTE)],alpha=.15)
        ax.set_ylabel(d.get("y_label","Density"))
    ax.grid(axis="y",alpha=.2)
    ax.legend(frameon=False,loc="best")


def _draw_radar(ax,d):
    angles=np.linspace(0,2*np.pi,len(d["axes"]),endpoint=False)
    closed=np.r_[angles,angles[0]]
    ax.set_theta_offset(np.pi/2)
    ax.set_theta_direction(-1)
    for i,s in enumerate(d["series"]):
        values=np.r_[s["values"],s["values"][0]]
        ax.plot(closed,values,color=PALETTE[i%len(PALETTE)],label=s["name"],linewidth=2,marker="o",markersize=4)
        ax.fill(closed,values,color=PALETTE[i%len(PALETTE)],alpha=.12)
    ax.set_xticks(angles,d["axes"])
    ax.set_ylim(d["range"])
    ax.set_yticks(np.linspace(d["range"][0],d["range"][1],6)[1:])
    ax.tick_params(axis="x",pad=12)
    ax.grid(alpha=.3)
    ax.spines["polar"].set_color("#CBD4DC")
    ax.legend(frameon=False,loc="upper right",bbox_to_anchor=(1.25,1.1))


def _draw_proportion(fig,d):
    rings=d["rings"]
    if d.get("layout","concentric")=="side_by_side":
        axes=np.atleast_1d(fig.subplots(1,len(rings)))
        all_labels=list(dict.fromkeys(l for ring in rings for l in ring["labels"]))
        colors={l:PALETTE[i%len(PALETTE)] for i,l in enumerate(all_labels)}
        for ax,ring in zip(axes,rings):
            wedge={"width":d.get("ring_width",.42)} if d.get("donut",True) else {}
            ax.pie(ring["values"],labels=ring["labels"],autopct="%1.1f%%",startangle=90,counterclock=False,colors=[colors[x] for x in ring["labels"]],wedgeprops={"edgecolor":"white","linewidth":2,**wedge},textprops={"fontsize":10},pctdistance=.78 if wedge else .65)
            ax.set_title(ring.get("name",""),pad=18)
        return
    ax=fig.subplots()
    ring_width=min(.3,.85/len(rings))
    legend_labels=[]; legend_handles=[]
    for i,ring in enumerate(rings):
        radius=1-i*ring_width
        palette=[PALETTE[(j+i*2)%len(PALETTE)] for j in range(len(ring["labels"]))]
        wedges,_,_=ax.pie(ring["values"],radius=radius,autopct="%1.1f%%",pctdistance=1-ring_width/(2*radius),startangle=90,counterclock=False,colors=palette,wedgeprops={"width":ring_width-.025,"edgecolor":"white","linewidth":1.5},textprops={"fontsize":9})
        legend_handles.extend(wedges)
        prefix=ring.get("name",f"Ring {i+1}")
        legend_labels.extend(f"{prefix}: {l}" for l in ring["labels"])
    ax.legend(legend_handles,legend_labels,loc="center left",bbox_to_anchor=(1.02,.5),frameon=False,fontsize=10)
    if len(rings)>1:
        ax.text(0,0,"Independent\ndistributions",ha="center",va="center",fontsize=10,color="#5A6875")
    ax.set_aspect("equal")


def _normalise_svg(text,width,height,metadata):
    ET.register_namespace("",SVG)
    ET.register_namespace("xlink","http://www.w3.org/1999/xlink")
    root=ET.fromstring(text)
    # Explicit SVG presentation attributes work in browsers and PDF converters.
    # Generic sans-serif avoids converters treating a CSS font list as one unknown name.
    for element in root.iter():
        style = element.attrib.pop("style", "")
        for declaration in style.split(";"):
            if ":" not in declaration:
                continue
            key, value = declaration.split(":", 1)
            element.set(key.strip(), value.strip())
        if "font-family" in element.attrib:
            element.set("font-family", "sans-serif")
    original=[float(x) for x in root.attrib["viewBox"].split()]
    root.set("width",str(width));root.set("height",str(height));root.set("viewBox",f"0 0 {width} {height}")
    root.set("role","img")
    root.set("aria-label",metadata.get("title","Scientific figure"))
    desc=ET.Element(f"{{{SVG}}}desc");desc.text=json.dumps(metadata,ensure_ascii=False)
    children=list(root)
    group=ET.Element(f"{{{SVG}}}g",{"transform":f"scale({width/original[2]:.12g} {height/original[3]:.12g})"})
    for child in children:
        root.remove(child)
        group.append(child)
    root.append(desc);root.append(group)
    return ET.tostring(root,encoding="unicode")


def render_plot(spec):
    """Return an SVG with selectable text and explicit numeric pixel dimensions."""
    spec=validate_plot(spec)
    width=int(spec.get("width",1000));height=int(spec.get("height",650))
    d=spec["data"];typ=spec["type"]
    digest=hashlib.sha256(json.dumps(spec,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12]
    settings={"svg.fonttype":"none","svg.hashsalt":digest,"font.family":_font_family(),"font.size":11,"axes.labelsize":12,"axes.titlesize":16,"axes.titleweight":"normal","axes.labelcolor":"#243849","axes.edgecolor":"#82909C","xtick.color":"#33485A","ytick.color":"#33485A","text.color":"#162C3E","figure.facecolor":"white","savefig.facecolor":"white"}
    with matplotlib.rc_context(settings):
        fig=plt.figure(figsize=(width/100,height/100),dpi=100,layout="constrained")
        try:
            title=spec.get("title","")
            if title:fig.suptitle(title,fontsize=17,fontweight="normal")
            footer=[]
            if spec["data_status"]=="illustrative":footer.append("ILLUSTRATIVE DATA — replace before reporting results")
            elif spec["data_status"]=="digitized":footer.append("Approximate values digitized from a source figure")
            if d.get("uncertainty"):footer.append(d["uncertainty"])
            if d.get("baseline_note"):footer.append(d["baseline_note"])
            if footer:fig.supxlabel("  ·  ".join(footer),fontsize=8,color="#667787")
            if typ=="proportion":
                _draw_proportion(fig,d)
            else:
                ax=fig.add_subplot(111,projection="polar" if typ=="radar" else None)
                if typ=="bar":_draw_bar(ax,d)
                elif typ=="line":_draw_line(ax,d)
                elif typ=="matrix":_draw_matrix(fig,ax,d)
                elif typ=="scatter":_draw_scatter(ax,d)
                elif typ=="distribution":_draw_distribution(ax,d)
                elif typ=="radar":_draw_radar(ax,d)
                if typ not in {"radar","matrix"}:
                    # Preserve distribution's count/density default when no explicit y label exists.
                    if typ=="distribution" and "y_label" not in d:d["y_label"]=ax.get_ylabel()
                    _decorate(ax,d)
            stream=io.StringIO()
            fig.savefig(stream,format="svg",metadata={"Date":None,"Creator":"paper-figure-studio"})
            return _normalise_svg(stream.getvalue(),width,height,{"title":spec.get("title",""),"type":typ,"data_status":spec["data_status"],"source":spec.get("source","")})
        finally:
            plt.close(fig)
