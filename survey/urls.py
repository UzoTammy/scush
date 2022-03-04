from django.urls import path
from .views import *

urlpatterns = [
    path('home/', SurveyHomeView.as_view(), name='survey-home'),
    path('list/', SurveyListView.as_view(), name='survey-list'),
    path('create/', SurveyCreateView.as_view(), name='kids-create-survey'),
    path('code/', SurveyCodeView.as_view(), name='survey-update'),
    path('<str:pin>/update/', SurveyUpdateView.as_view(), name='survey-update'),
    path('reset/', SurveyResetView.as_view(), name='survey-reset'),
]

