from django.urls import path
from . import views
from apply.views import WelcomeView
from .views import SendMailView

urlpatterns = [
    path('welcome/', WelcomeView.as_view(), name='welcome'),
    path('mails/', SendMailView.as_view(), name='mail'),
]
