from django.urls import path
from . import views

urlpatterns = [
    path("", views.initsearch),
    path("initsearch", views.initsearch, name="initisearch"),
    path("getpatientid", views.getpatientid, name="getpatientid"),
    # path("displayinitialres", views.displayinitialres, name="displayinitialres"),
    # path("distillerrecsdispcmp", views.distillerrecsdispcmp, name="distillerrecsdispcmp"),
]
