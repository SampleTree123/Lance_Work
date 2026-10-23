"""Static scientific chart with ReportLab chart primitives; no environment changes."""
import csv
from pathlib import Path
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String, Line
from reportlab.graphics import renderSVG
from reportlab.lib import colors

root = Path(__file__).resolve().parent
rows = list(csv.DictReader((root / 'cost_curves.csv').open(encoding='utf-8-sig')))
canvas = Drawing(960, 370)
palette = [colors.HexColor(x) for x in ('#1D5E91', '#E07A29', '#33996D')]
for panel in (0, 1):
    chart = LinePlot()
    chart.x, chart.y, chart.width, chart.height = 65 + panel * 480, 82, 365, 235
    chart.joinedLines = 1
    if panel == 0:
        chart.data = [[(int(r['view_buckets']), int(r['action_clip_count'])) for r in rows
                       if int(r['carrier_count']) == carrier and int(r['timing_profiles_per_key']) == 1]
                      for carrier in (1, 2)]
        labels = ['1 neutral carrier', '2 sex-fit carriers']
        title, xlabel = 'Semantic-motion library', 'View buckets (planning categories)'
        chart.xValueAxis.valueMin, chart.xValueAxis.valueMax = 1, 21
        chart.xValueAxis.valueSteps = [1, 2, 4, 8, 21]
        chart.yValueAxis.valueMin, chart.yValueAxis.valueMax = 0, 500
        chart.yValueAxis.valueStep = 100
    else:
        chart.data = [[(int(r['timing_profiles_per_key']), int(r['action_clip_count'])) for r in rows
                       if int(r['carrier_count']) == 2 and int(r['view_buckets']) == views]
                      for views in (1, 4, 21)]
        labels = ['1 view', '4 view groups', '21 matched cameras']
        title, xlabel = 'Timing-profile full-coverage scenarios', 'Timing profiles per key (not observed)'
        chart.xValueAxis.valueMin, chart.xValueAxis.valueMax = 1, 8
        chart.xValueAxis.valueSteps = [1, 2, 4, 8]
        chart.yValueAxis.valueMin, chart.yValueAxis.valueMax = 0, 4000
        chart.yValueAxis.valueStep = 1000
    for i in range(len(chart.data)):
        chart.lines[i].strokeColor = palette[i]
        chart.lines[i].strokeWidth = 2
    chart.xValueAxis.labels.fontSize = chart.yValueAxis.labels.fontSize = 9
    canvas.add(chart)
    canvas.add(String(chart.x, 340, title, fontName='Helvetica-Bold', fontSize=12))
    canvas.add(String(chart.x + 130, 40, xlabel, fontSize=10, textAnchor='middle'))
    canvas.add(String(chart.x - 28, 205, 'Clips', fontSize=9, textAnchor='end'))
    for i, text in enumerate(labels):
        canvas.add(Line(chart.x + i * 122, 20, chart.x + i * 122 + 14, 20, strokeColor=palette[i], strokeWidth=2))
        canvas.add(String(chart.x + i * 122 + 18, 16, text, fontSize=8))
renderSVG.drawToFile(canvas, str(root / 'reference_cost_curves.svg'))
try:
    from reportlab.graphics import renderPM
    renderPM.drawToFile(canvas, str(root / 'reference_cost_curves.png'), fmt='PNG')
except Exception as error:
    print('SVG chart generated; optional PNG renderer unavailable:', type(error).__name__)
