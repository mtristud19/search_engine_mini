from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, CategoryViewSet, SearchView, AutocompleteView, TrendingDocumentsView, SearchAsYouTypeView, TestUpdateDate, SimilarDocumentsView

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    path("search/suggest/", AutocompleteView.as_view(), name="search-suggest"),
    path("search/as-you-type/", SearchAsYouTypeView.as_view(), name="search-as-you-type"),
    path("search/trending/", TrendingDocumentsView.as_view(), name="search-trending"),
    path("test-update/", TestUpdateDate.as_view(), name="test-update"),
    path("documents/<uuid:document_id>/similar/", SimilarDocumentsView.as_view(), name="search-similar-documents"),
    path("", include(router.urls)),
]
