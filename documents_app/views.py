import hashlib
from django.core.cache import cache
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Document, Category
from .serializers import DocumentSerializer, CategorySerializer, SearchResultSerializer
from .documents import DocumentIndex

CACHE_TTL_SECONDS = 300


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD cho Category — dùng để gán category_id khi tạo Document."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class DocumentViewSet(viewsets.ModelViewSet):
    """CRUD chuẩn — ghi vào PostgreSQL.

    post_save/post_delete signal sẽ tự động đồng bộ sang Elasticsearch,
    nên view này không cần biết gì về search index cả.
    """

    queryset = Document.objects.select_related("category").all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class SearchView(APIView):
    """Full-text search, hỗ trợ filter theo category/tags + trả về facet counts.
    Check Redis cache trước (cache key gồm cả filter), miss thì query Elasticsearch.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        page = int(request.query_params.get("page", 1))
        category_slug = request.query_params.get("category", "").strip()
        tags = [t for t in request.query_params.get("tags", "").split(",") if t]

        if not query:
            return Response({"results": [], "count": 0, "facets": {}})

        cache_key = self._build_cache_key(query, page, category_slug, tags)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        search = (
            DocumentIndex.search()
            .query("multi_match", query=query, fields=["title^3", "content"])
            .highlight("content", fragment_size=150)
            .filter("term", is_published=True)
        )

        if category_slug:
            search = search.filter("term", category__slug=category_slug)
        for tag in tags:
            # filter từng tag riêng -> AND semantics: document phải có đủ tất cả tag được chọn
            search = search.filter("term", tags=tag)

        # Facet tính trên toàn bộ kết quả khớp query/filter, không bị giới hạn bởi pagination
        search.aggs.bucket("by_category", "terms", field="category.slug", size=20)
        search.aggs.bucket("by_tags", "terms", field="tags", size=20)

        start = (page - 1) * 10
        response = search[start:start + 10].execute()

        results = []
        for hit in response:
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
            "results": SearchResultSerializer(results, many=True).data,
            "count": response.hits.total.value,
            "facets": {
                "categories": [
                    {"slug": bucket.key, "count": bucket.doc_count}
                    for bucket in response.aggregations.by_category.buckets
                ],
                "tags": [
                    {"value": bucket.key, "count": bucket.doc_count}
                    for bucket in response.aggregations.by_tags.buckets
                ],
            },
        }
        cache.set(cache_key, payload, CACHE_TTL_SECONDS)
        return Response(payload)

    @staticmethod
    def _build_cache_key(query, page, category_slug, tags):
        raw = f"search:{query.lower()}:{page}:{category_slug}:{','.join(sorted(tags))}"
        return hashlib.sha256(raw.encode()).hexdigest()


class AutocompleteView(APIView):
    """Gợi ý title khi người dùng đang gõ — dùng completion suggester của Elasticsearch.
    Không qua Redis cache vì completion suggester đã rất nhanh (FST nội bộ của ES).
    """

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
