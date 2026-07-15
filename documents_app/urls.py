from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, CategoryViewSet, SearchView, AutocompleteView, TrendingDocumentsView

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    path("search/suggest/", AutocompleteView.as_view(), name="search-suggest"),
    path("search/trending/", TrendingDocumentsView.as_view(), name="search-trending"),
    path("", include(router.urls)),
]
