from django.urls import path
from . import views

urlpatterns = [
    path("", views.index),
    path("gengraph", views.gengraph, name="gengraph"),
    path("initsearch", views.initsearch, name="initisearch"),
    path("getpatientid", views.getpatientid, name="getpatientid"),
    # path("displayinitialres", views.displayinitialres, name="displayinitialres"),
    # path("distillerrecsdispcmp", views.distillerrecsdispcmp, name="distillerrecsdispcmp"),
]
