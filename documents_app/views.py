import hashlib
from datetime import datetime, time, timedelta
import random

from django.core.cache import cache
from django.db.models import F
from django.utils import timezone
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
from .throttle import SlidingWindowThrottle
from .utils import get_client_ip

CACHE_TTL_SECONDS = 300
TRACKING_TTL_SECONDS = 600
TRENDING_KEY = "search:trending"
# Redis allows offsets up to 2^32-1, but hashing across that full range can
# allocate nearly 512 MB for one document/day. Cap each bitmap at ~1.25 MB.
MAX_BITMAP_OFFSET = 10_000_000
HIGHLIGHT_OPTIONS = {
    "type": "fvh",
    "number_of_fragments": 3,
    "fragment_size": 100,
    "phrase_limit": 256,
}

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
        if self._mark_viewed_today(request, instance.id):
            Document.objects.filter(pk=instance.pk).update(view_count=F("view_count") + 1)
            instance.refresh_from_db(fields=["view_count"])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @staticmethod
    def _mark_viewed_today(request, document_id):
        """Set today's viewer bit and return True only for a first daily view."""
        if request.user.is_authenticated:
            viewer_identity = f"user:{request.user.pk}"
        else:
            viewer_identity = f"ip:{get_client_ip(request) or 'unknown'}"
        
        # Redis bit offsets must be integers. Keep the hash in the configured
        # range 1..MAX_BITMAP_OFFSET rather than using an IP/user string.
        digest = hashlib.blake2b(viewer_identity.encode(), digest_size=8).digest() 
        bit_offset = int.from_bytes(digest, "big") % MAX_BITMAP_OFFSET + 1

        today = timezone.localdate()
        date_key = today.isoformat()
        bitmap_key = f"viewed:{date_key}:{document_id}"
        next_midnight = timezone.make_aware(
            datetime.combine(today + timedelta(days=1), time.min),
            timezone.get_current_timezone(),
        )
        
        # SETBIT returns the previous value atomically. Therefore concurrent
        # first views from one identity can increment the database only once.
        redis_client = cache.client.get_client()
        
        pipeline = redis_client.pipeline(transaction=True)
        pipeline.setbit(bitmap_key, bit_offset, 1)
        pipeline.expireat(bitmap_key, int(next_midnight.timestamp()))
        previous_bit, _ = pipeline.execute()
        
        return previous_bit == 0

class SearchView(APIView):
    """ API endpoint for searching documents using Elasticsearch. """
    
    permission_classes = [permissions.AllowAny]
    throttle_classes = [SlidingWindowThrottle]

    def get(self, request):
        
        query = request.query_params.get("q", "").strip()
        page = int(request.query_params.get("page", 1))
        category_filter = request.query_params.get("category", "").strip().lower()
        tags_filter = request.query_params.get("tags", "").strip().lower()
        debug = request.query_params.get("debug", "").strip()
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
            .highlight("content", **HIGHLIGHT_OPTIONS)
            .filter("term", is_published=True)
        )
        
        search = self.apply_filters(search, category_filter, tags_filter)
        
        search = self.apply_aggregations(search)
        
        if debug:
            search = search.extra(explain=True)  # For debugging purposes
        
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
                .highlight("content", **HIGHLIGHT_OPTIONS)
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
                "explanation": hit.meta.explanation if hasattr(hit.meta, "explanation") else None,
            })

        payload = {
            "count": response.hits.total.value,
            "did_you_mean": did_you_mean,
            "results": SearchResultSerializer(results, many=True).data,
            "facets": {
                "by_month": [
                    {"month": b.key_as_string, "count": b.doc_count}
                    for b in response.aggregations.recent_6_months_only.documents_per_month.buckets
                ],
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
        
        aggs_filter = search.aggs.bucket(
            "recent_6_months_only",
            "filter", 
            filter={"range": {"created_at": {"gte": "now-5M/M", "lte": "now"}}}
        )
        aggs_filter.bucket(
            "documents_per_month",
            "date_histogram",
            field="created_at",
            calendar_interval="month",
            format="yyyy-MM",
            min_doc_count=0,
            extended_bounds={"min": "now-5M/M", "max": "now"},
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

class SearchAsYouTypeView(APIView):
    """ Provide search-as-you-type functionality using Elasticsearch's search_as_you_type field. """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"results": []})

        search = DocumentIndex.search().query(
            "multi_match",
            query=query,
            type="bool_prefix",
            fields=[
                "title_search",
                "title_search._2gram",
                "title_search._3gram",
            ]
        )

        response = search[0:10].execute()
        results = [
            hit.title
            for hit in response
        ]
        return Response({"results": results})
class TestUpdateDate(APIView):
    """ Provide search-as-you-type functionality using Elasticsearch's search_as_you_type field. """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        
        documents = Document.objects.all()
        updates = []
        for doc in documents:
            day_update = random.randint(0, 150)
            day_create = random.randint(day_update, 300)
            doc.updated_at = timezone.now() - timedelta(days=day_update)
            doc.created_at = timezone.now() - timedelta(days=day_create)
            print(f"Updating document {doc.id} date to {doc.created_at} - {doc.updated_at}")
            updates.append(doc)

        Document.objects.bulk_update(updates, ["created_at", "updated_at"])
        
        return Response({"message": f"Updated {len(updates)} documents' created_at dates."})
    
class SimilarDocumentsView(APIView):
    """ API endpoint for retrieving documents similar to a given document. """

    permission_classes = [permissions.AllowAny]

    def get(self, request, document_id):
        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=404)

        search = DocumentIndex.search().query(
            "more_like_this",
            fields=["title", "content"],
            like=[{"_id": document_id}],
            min_term_freq=1,
            max_query_terms=12,
            min_doc_freq=1,
        ).filter("term", is_published=True).exclude("term", _id=document_id)

        response = search[0:5].execute()
        results = [
            {
                "id": hit.meta.id,
                "title": hit.title,
                "snippet": hit.content[:150],
                "category": getattr(hit.category, "name", None) if hasattr(hit, "category") else None,
                "tags": list(hit.tags) if hasattr(hit, "tags") else [],
                "score": hit.meta.score,
            }
            for hit in response
        ]

        return Response({
            "results": SearchResultSerializer(results, many=True).data
        })
