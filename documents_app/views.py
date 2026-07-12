import hashlib
from django.core.cache import cache
from elasticsearch_dsl import search
from rest_framework import request, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from rest_framework.throttling import AnonRateThrottle
from django.db.models import F

from .models import Document, Category
from .serializers import DocumentSerializer, CategorySerializer, SearchResultSerializer
from .documents import DocumentIndex

CACHE_TTL_SECONDS = 300
TRACKING_TTL_SECONDS = 600

class CategoryViewSet(viewsets.ModelViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class DocumentViewSet(viewsets.ModelViewSet):

    queryset = Document.objects.select_related("category").all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [OrderingFilter]
    ordering_fields = [
            "created_at",
            "view_count"
        ]
    ordering = ["-created_at"]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Document.objects.filter(pk=instance.pk).update(view_count=F("view_count") + 1)
        instance.refresh_from_db(fields=["view_count"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class SearchView(APIView):
    """ API endpoint for searching documents using Elasticsearch. """
    
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        page = int(request.query_params.get("page", 1))
        category_filter = request.query_params.get("category", "").strip().lower()
        tags_filter = request.query_params.get("tags", "").strip().lower()

        if not query:
            return Response({"results": [], "count": 0})

        cache_key = self._build_cache_key(query, page, category_filter, tags_filter)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        search = (
            DocumentIndex.search()
            .query("multi_match", query=query, fields=["title^3", "content"])
            .highlight("content", fragment_size=150)
            .filter("term", is_published=True)
        )
        
        if category_filter:
            search = search.filter("term", **{"category__slug": category_filter})
        if tags_filter:
            search = search.filter("term", tags=tags_filter)
        
        search.aggs.bucket("categories", "terms", field="category.slug")
        search.aggs.bucket("tags", "terms", field="tags")
        
        start = (page - 1) * 10
        response = search[start:start + 10].execute()

        results = []
        document_ids = []
        for hit in response:
            document_ids.append(hit.meta.id)
            snippet = (
                " ".join(hit.meta.highlight.content)
                if "highlight" in hit.meta
                else hit.content[:150]
            )
            results.append({
                "id": hit.meta.id,
                "title": hit.title,
                "snippet": snippet,
                "category": getattr(hit.category, "name", None) if hasattr(hit, "category") else None,
                "tags": list(hit.tags) if hasattr(hit, "tags") else [],
                "score": hit.meta.score,
            })

        payload = {
            "count": response.hits.total.value,
            "results": SearchResultSerializer(results, many=True).data,
            "facets": {
                "categories": [
                    {"slug": b.key, "count": b.doc_count}
                    for b in response.aggregations.categories.buckets
                ],
                "tags": [
                    {"value": b.key, "count": b.doc_count}
                    for b in response.aggregations.tags.buckets
                ],
            }
        }
        cache.set(cache_key, payload, CACHE_TTL_SECONDS)

        # Register the cache_key in the tracking set for each document_id, 
        # so that when a document is updated or deleted, we can invalidate the relevant cache entries.
        self._register_tracking(cache_key, document_ids)

        return Response(payload)

    @staticmethod
    def _build_cache_key(query, page, category_filter="", tags_filter=""):
        raw = f"search:{query.lower()}:{page}:{category_filter}:{tags_filter}"
        # print(f"Building cache key for search: {raw}")
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _register_tracking(cache_key, document_ids):
        if not document_ids:
            return
        redis_client = cache.client.get_client()
        pipeline = redis_client.pipeline()  # 1 round-trip
        for doc_id in document_ids:
            tracking_key = f"search:tracking:{doc_id}"
            pipeline.sadd(tracking_key, cache_key)
            pipeline.expire(tracking_key, TRACKING_TTL_SECONDS)
        pipeline.execute()

class AutocompleteView(APIView):
    """ Suggest titles as the user types — using Elasticsearch's completion suggester. """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        prefix = request.query_params.get("q", "").strip()
        if not prefix:
            return Response({"suggestions": []})

        search = DocumentIndex.search().suggest(
            "title-suggest", prefix,
            completion={"field": "title_suggest", "size": 5, "skip_duplicates": True},
        )
        response = search.execute()

        suggestions = [
            option.text
            for option in response.suggest["title-suggest"][0].options
        ]
        return Response({"suggestions": suggestions})
