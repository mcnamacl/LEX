from django.urls import path
from . import views

urlpatterns = [
    path("", views.index),
    path("displayResults", views.displayResults, name="displayResults"),
    path("displayPatientInformation", views.displayPatientInformation, name="displayPatientInformation"),
]
