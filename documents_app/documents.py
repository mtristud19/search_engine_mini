from django_elasticsearch_dsl import Document as ESDocument, fields
from django_elasticsearch_dsl.registries import registry
from .models import Document


@registry.register_document
class DocumentIndex(ESDocument):
    category = fields.ObjectField(properties={
        "name": fields.TextField(),
        "slug": fields.KeywordField(),
    })
    tags = fields.KeywordField(multi=True)
    title_suggest = fields.CompletionField()
    title = fields.TextField(analyzer="vietnamese")
    content = fields.TextField(analyzer="vietnamese")
    
    class Index:
        name = "documents"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "vietnamese": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"],
                    }
                }
            }
        }

    class Django:
        model = Document
        fields = [
            "author",
            "is_published",
            "created_at",
        ]

    def get_queryset(self):
        return super().get_queryset().select_related("category")

    def prepare_title_suggest(self, instance):
        return instance.title
