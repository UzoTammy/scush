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
