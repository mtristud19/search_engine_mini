from django.db import models
import uuid
from django.contrib.postgres.fields import ArrayField
# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    
class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="documents"
    )
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    author = models.CharField(max_length=150)
    is_published = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "is_published"], name="doc_category_pub_idx"),
            models.Index(fields=["created_at"], name="doc_created_at_idx"),
        ]

    def __str__(self):
        return self.title