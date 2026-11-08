"""Small native HTML inspection views, without a browser chart runtime."""

from html import escape
import math


def ranking_html(rows, method):
    """Preserve rank order and a shared zero baseline, including signed scores."""
    if not rows:
        return ""
    if any(not math.isfinite(score) for _, score in rows):
        raise ValueError("Ranking scores must be finite")
    scale = max(abs(score) for _, score in rows) or 1
    origin = 50 if any(score < 0 for _, score in rows) else 0
    parts = ["""<style>
    .ece-ranking {margin:0; width:100%;}
    .ece-ranking figcaption {font-weight:600; margin-bottom:.75rem;}
    .ece-ranking ol {list-style:none; margin:0; padding:0;}
    .ece-ranking li {display:grid; grid-template-columns:minmax(0,2fr) minmax(60px,3fr) max-content;
                     gap:.65rem; align-items:center; margin:.55rem 0; font-size:.875rem;}
    .ece-ranking-label {overflow-wrap:anywhere; min-width:0;}
    .ece-ranking-track {position:relative; height:.8rem; background:rgba(120,184,255,.08);}
    .ece-ranking-axis {position:absolute; top:0; bottom:0; width:1px; background:currentColor; opacity:.35;}
    .ece-ranking-bar {position:absolute; top:.12rem; bottom:.12rem; background:#78B8FF; border-radius:2px;}
    .ece-ranking-value {font-variant-numeric:tabular-nums;}
    </style>""", '<figure class="ece-ranking" data-ece-ranking="html" aria-label="Ranking scores">',
             "<figcaption>" + escape(str(method)) + " ranking score</figcaption><ol>"]
    for label, score in rows:
        # Divide before multiplying to keep extreme finite scores finite.
        width = abs(score) / scale * (origin if score < 0 else 100 - origin)
        left = origin - width if score < 0 else origin
        parts.append('<li><span class="ece-ranking-label">' + escape(str(label)) + '</span>'
                     '<span class="ece-ranking-track" aria-hidden="true">'
                     f'<span class="ece-ranking-axis" style="left:{origin}%"></span>'
                     f'<span class="ece-ranking-bar" style="left:{left:.6f}%;width:{width:.6f}%"></span></span>'
                     '<span class="ece-ranking-value" title="' + escape(str(score)) + '">'
                     + escape(format(score, ".6g")) + '</span></li>')
    parts.append('</ol></figure>')
    return "".join(parts)
