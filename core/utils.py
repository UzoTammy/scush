import matplotlib.pyplot as plt
import base64
from io import BytesIO

def get_graph():
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    graph = base64.b64encode(image_png).decode('utf-8')
    buffer.close()
    return graph

def sales_stock_figure(x, y):
    plt.switch_backend('AGG')
    plt.figure(figsize=(4, 4))
    plt.title('Sales Trend')
    plt.barh(x, y)
    plt.ylabel('Date')
    plt.xlabel('Sales vs Stock(%)')
    plt.tight_layout()
    graph = get_graph()
    return graph

def monthly_sales_revenue(x, y):
    plt.switch_backend('AGG')
    plt.figure(figsize=(4, 4))
    plt.title('Monthly Sales Revenue')
    plt.barh(x, y)
    plt.ylabel('month')
    plt.xlabel('Sales (N)')
    plt.tight_layout()
    graph = get_graph()
    return graph

def margin_graph(x, y):
    plt.switch_backend('AGG')
    plt.figure(figsize=(4, 3))
    plt.title('Margin Ratio')
    plt.bar(x, y)
    plt.ylabel('Ratio')
    plt.xlabel('Day in Date')
    plt.tight_layout()
    graph = get_graph()
    return graph


# custom Fuction
def string_float(text):
    digit = str()
    text = text.strip()
    factor = -1 if text[0] == '-' else 1
    for t in text:
        digit += t if t.isdigit() or t == '.' else ""
    return float(digit) * factor


def line_plot(x, y, title, y_axis, x_axis):
    plt.switch_backend('AGG')
    plt.figure(figsize=(4, 3))
    plt.title(title)
    plt.plot(x, y, marker='o', color='red', linestyle='dashed', markerfacecolor='blue', markersize=2, linewidth=1)
    plt.ylabel(y_axis)
    plt.xlabel(x_axis)
    plt.tight_layout()
    graph = get_graph()
    return graph 

def bar_plot(x, y, title, y_axis, x_axis):
    plt.switch_backend('AGG')
    plt.figure(figsize=(4, 3))
    plt.title(title)
    plt.bar(x, y, color='lightblue')
    plt.ylabel(y_axis)
    plt.xlabel(x_axis)
    plt.tight_layout()
    graph = get_graph()
    return graph

def donut(items, values, title, legend=0, legends=None, text=""):
    plt.switch_backend('AGG')
    n = len(items)
    if n != len(values):
        return None
    colors = ('#FF0000', '#ADD8E6', '#FFFF00', '#ADFF2F', '#FFA500', '#90EE90')
    explode = list(0.05 for _ in range(0, n))
    plt.pie(values, colors=colors, labels=items, autopct='%1.2f%%', pctdistance=0.85, explode=explode)
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    plt.title(title)
    plt.text(-1.5, -1.5, text, ha='left', va='bottom', fontsize=16, fontweight='bold')
    if legend == 1:
        plt.legend(legends, loc='center')
    graph = get_graph()
    return graph 