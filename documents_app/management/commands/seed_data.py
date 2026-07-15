from django.core.management.base import BaseCommand
import random
from faker import Faker
from django.utils.text import slugify
from django.utils import timezone
from documents_app.documents import DocumentIndex

from documents_app.models import Category, Document
from documents_app.management.commands.const import CATEGORIES, TAGS, TITLE_TEMPLATES, CONTENT_TEMPLATES

fake = Faker()

class Command(BaseCommand):
    help = "Seed database with fake documents"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Number of documents to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def delete_existing_data(self):
        
        self.stdout.write("Deleting existing data...")

        Document.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS("✓ Existing data deleted.")
        )
    
    def generate_title(self):
        tag = random.choice(TAGS)
        template = random.choice(TITLE_TEMPLATES)
        return template.format(tag.title())

    def generate_content(self):
        paragraphs = []

        for _ in range(random.randint(3, 5)):
            keyword = random.choice(TAGS)

            paragraphs.append(
                f"""
                {fake.paragraph(nb_sentences=5)}

                {random.choice(CONTENT_TEMPLATES).format(keyword)}

                {fake.paragraph(nb_sentences=6)}
                """
            )

        return "\n".join(paragraphs)

    def handle(self, *args, **options):
        count = options["count"]
    
        if options["clear"]:
            self.delete_existing_data()

        self.stdout.write("Creating categories...")

        categories = {}

        for name in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={
                    "slug": slugify(name)
                },
            )
            categories[name] = category

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {len(categories)} categories ready"
            )
        )

        authors = [fake.name() for _ in range(30)]
        
        documents = []

        self.stdout.write(f"Generating {count} documents...")

        for _ in range(count):

            document = Document(
                title=self.generate_title(),
                content=self.generate_content(),
                category=random.choice(list(categories.values())),
                tags=random.sample(TAGS, random.randint(2, 5)),
                author=random.choice(authors),
                is_published=random.random() < 0.9,
                view_count=random.randint(0, 50000),
            )

            documents.append(document)

        Document.objects.bulk_create(documents)

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Successfully created {count} documents."
            )
        )
        
        DocumentIndex().update(Document.objects.all().iterator(chunk_size=500))
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Successfully updated document index."
            )
        )
