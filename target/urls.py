from django.urls import path
from .views import (
    TargetHomeView,
    BudgetYearListView, BudgetYearDetailView,
    BudgetYearCreateView, BudgetYearUpdateView,
    SalesTargetCreateView, SalesTargetUpdateView,
    KPIBudgetCreateView, KPIBudgetUpdateView,
    KPIMonthlyTargetCreateView, KPIMonthlyTargetUpdateView,
)

urlpatterns = [
    path('home/', TargetHomeView.as_view(), name='target-home'),

    # Budget year
    path('budget/', BudgetYearListView.as_view(), name='budget-year-list'),
    path('budget/create/', BudgetYearCreateView.as_view(), name='budget-year-create'),
    path('budget/<int:pk>/', BudgetYearDetailView.as_view(), name='budget-year-detail'),
    path('budget/<int:pk>/update/', BudgetYearUpdateView.as_view(), name='budget-year-update'),

    # Sales monthly targets
    path('budget/<int:year_pk>/sales/create/', SalesTargetCreateView.as_view(), name='sales-target-create'),
    path('sales/<int:pk>/update/', SalesTargetUpdateView.as_view(), name='sales-target-update'),

    # KPI annual budgets
    path('budget/<int:year_pk>/kpi-budget/create/', KPIBudgetCreateView.as_view(), name='kpi-budget-create'),
    path('kpi-budget/<int:pk>/update/', KPIBudgetUpdateView.as_view(), name='kpi-budget-update'),

    # KPI monthly targets
    path('budget/<int:year_pk>/kpi-monthly/create/', KPIMonthlyTargetCreateView.as_view(), name='kpi-monthly-create'),
    path('kpi-monthly/<int:pk>/update/', KPIMonthlyTargetUpdateView.as_view(), name='kpi-monthly-update'),
]
