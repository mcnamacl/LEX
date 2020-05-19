from django.urls import path
from . import views

urlpatterns = [
    path("", views.index),
    path("getpatientid", views.getpatientid, name="getpatientid"),
    # path("displayinitialres", views.displayinitialres, name="displayinitialres"),
    # path("distillerrecsdispcmp", views.distillerrecsdispcmp, name="distillerrecsdispcmp"),
]
