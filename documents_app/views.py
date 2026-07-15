import hashlib
from django.core.cache import cache
from elasticsearch_dsl import query, search, Q
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
TRENDING_KEY = "search:trending"

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
        did_you_mean = False 
        base_params = {
            "query": query,
            "fields": ["title^3", "tags^2", "content"],
        }

        if not query:
            return Response({"results": [], "count": 0})

        cache_key = self._build_cache_key(query, page, category_filter, tags_filter)
        cached = cache.get(cache_key)
        
        if cached is not None:
            self._track_trending(query) # Track the search query for trending purposes
            cache.touch(cache_key, CACHE_TTL_SECONDS)  # Refresh the cache TTL
            return Response(cached)

        query_dsl = Q("multi_match", **base_params)
        
        search = (
            DocumentIndex.search()
            .query(query_dsl)
            .highlight("content", fragment_size=150)
            .filter("term", is_published=True)
        )
        
        search = self.apply_filters(search, category_filter, tags_filter)
        
        search = self.apply_aggregations(search)
        
        start = (page - 1) * 10
        response = search[start:start + 10].execute()

        # Fuzzy search fallback if no results found
        if response.hits.total.value == 0:
            
            fuzzy_params = { 
                "max_expansions": 50,
                "fuzziness": "AUTO",
            }
            
            fuzzy_query_dsl = Q("multi_match", **base_params, **fuzzy_params)
            fuzzy_search = (
                DocumentIndex.search()
                .query(fuzzy_query_dsl)
                .highlight("content", fragment_size=150)
                .filter("term", is_published=True)
            )
            
            fuzzy_search = self.apply_filters(fuzzy_search, category_filter, tags_filter)
            fuzzy_search = self.apply_aggregations(fuzzy_search)
            
            response = fuzzy_search[start:start + 10].execute()
            
            if response.hits.total.value != 0:
                did_you_mean = True

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
            "did_you_mean": did_you_mean,
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
        
        if not did_you_mean and response.hits.total.value > 0:
            # Cache the results only if they are not from a fuzzy search
            cache.set(cache_key, payload, CACHE_TTL_SECONDS)
            
            # Register the cache_key in the tracking set for each document_id, 
            # so that when a document is updated or deleted, we can invalidate the relevant cache entries.
            self._register_tracking(cache_key, document_ids)
            
            self._track_trending(query) # Track the search query for trending purposes
        
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
    
    @staticmethod   
    def apply_filters(search, category_filter=None, tags_filter=None):
        """
        Apply optional filters to the Elasticsearch search object.
        """
        if category_filter:
            search = search.filter(
                "term",
                **{"category__slug": category_filter},
            )
        if tags_filter:
            search = search.filter(
                "term",
                tags=tags_filter,
            )

        return search

    @staticmethod
    def apply_aggregations(search):
        """
        Add aggregations for categories and tags.
        """
        search.aggs.bucket(
            "categories",
            "terms",
            field="category.slug",
        )
        search.aggs.bucket(
            "tags",
            "terms",
            field="tags",
        )

        return search
    
    @staticmethod
    def _track_trending(query):
        try:
            redis_client = cache.client.get_client()
            redis_client.zincrby(TRENDING_KEY, 1, query.lower())
        except AttributeError:
            pass

class TrendingDocumentsView(APIView):
    """ API endpoint for retrieving trending documents based on view counts. """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """ Retrieve the top trending search queries from Redis. """
        
        try:
            redis_client = cache.client.get_client()
            results = redis_client.zrevrange(
                TRENDING_KEY, 0, 9, withscores=True
            )
            
            trending = [
                {"query": item[0].decode(), "count": int(item[1])}
                for item in results
            ]
        except AttributeError:
            trending = []

        return Response({"trending": trending})

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
