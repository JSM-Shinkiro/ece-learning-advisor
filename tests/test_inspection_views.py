"""Signed scores, literal source labels and degenerate ranking views."""

from html.parser import HTMLParser

import pytest

from src.inspection_views import ranking_html


class Chart(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.bars=[];self.values=[];self.text=[]
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if attrs.get('class')=='ece-ranking-bar':self.bars.append(attrs['style'])
        if attrs.get('class')=='ece-ranking-value':self.values.append(attrs['title'])
    def handle_data(self, value):self.text.append(value)


def test_signed_ranking_uses_one_zero_axis_and_keeps_order_and_numeric_values():
    chart=Chart(ranking_html([('negative',-.8),('positive',.4),('zero',0.0)],'semantic'))
    assert chart.bars==['left:0.000000%;width:50.000000%',
                        'left:50.000000%;width:25.000000%','left:50.000000%;width:0.000000%']
    assert chart.values==['-0.8','0.4','0.0']
    assert chart.text.index('negative')<chart.text.index('positive')<chart.text.index('zero')


def test_zero_and_extreme_finite_scores_have_bounded_bars():
    assert Chart(ranking_html([('zero',0)],'keyword')).bars==['left:0.000000%;width:0.000000%']
    assert Chart(ranking_html([('maximum',1e308),('half',5e307)],'keyword')).bars==[
        'left:0.000000%;width:100.000000%','left:0.000000%;width:50.000000%']
    assert ranking_html([],'keyword')==''


def test_source_labels_and_method_are_literal_text_without_executable_markup():
    label='<img src=x onerror="alert(1)"> & course'
    html=ranking_html([(label,1/3)],'<script>alert(2)</script>')
    assert '<img' not in html and '<script' not in html
    assert label in Chart(html).text and '<script>alert(2)</script> ranking score' in Chart(html).text
    assert Chart(html).values==[str(1/3)]


@pytest.mark.parametrize('score',[float('nan'),float('inf'),-float('inf')])
def test_nonfinite_scores_cannot_generate_invalid_chart_geometry(score):
    with pytest.raises(ValueError):ranking_html([('invalid',score)],'hybrid')
