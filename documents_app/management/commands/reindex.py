from time import time

from django.core.management.base import BaseCommand
from elasticsearch_dsl import mapping
from documents_app.documents import DocumentIndex

from elasticsearch import Elasticsearch
from django.conf import settings

from documents_app.models import Document

ALIAS = "documents"

class Command(BaseCommand):
    help = "Reindex the Elasticsearch index for documents without downtime (using alias swap)"

    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.es = Elasticsearch(
            settings.ELASTICSEARCH_DSL["default"]["hosts"]
        )

    def handle(self, *args, **options):
        start = time()
        current = self.get_current_index()
 
        if current is None:
            self.migrate_to_alias()
        else:
            self.reindex(current)
 
        elapsed = round(time() - start, 2)
        self.stdout.write(self.style.SUCCESS(
            f"Zero-downtime reindex complete in {elapsed}s"
        ))
        
    def get_current_index(self):
        """"""
        try:
            aliases = self.es.indices.get_alias(name=ALIAS)
            return list(aliases.keys())[0]
        except Exception:
            return None
        
    def get_new_index_name(self, current_index):
        """Determine the new index name based on the current index. If the current index is None, return the first version."""
        
        new_version = self.get_new_version_index_name(current_index)
        new_index = f"{ALIAS}_v{new_version}"
        self.stdout.write(self.style.WARNING(f"New index name: {new_index}"))
        return new_index
    
    def get_new_index_name(self, current):
        """Swap between v1 - v2."""
        version = int(current.split("_v")[-1])
        next_version = (version % 2) + 1
        return f"{ALIAS}_v{next_version}"
    
    def create_index(self, index_name):
        """Create a new index with the same settings as the current index."""
        
        if self.es.indices.exists(index=index_name):
            self.stdout.write(f"  Index {index_name} exists, deleting...")
            self.es.indices.delete(index=index_name)
        
        mapping = DocumentIndex._index.to_dict()
        self.es.indices.create(index=index_name, body=mapping)
        
    def reindex_data(self, source, destination):
        """Reindex data from the source index to the destination index."""
        
        self.stdout.write(self.style.NOTICE(f"Reindexing data from {source} to {destination}..."))
        count = Document.objects.count()
        self.stdout.write(f"  Reindexing {count} documents...")
        try:
            # self.es.reindex(body={
            #         "source": {"index": source},
            #         "dest": {"index": destination}
            #     },
            #     wait_for_completion=True,
            # )
            
            # Reindex data from Database to mapping field in DocumentIndex
            index = DocumentIndex()
            index._index._name = destination
            index.update(Document.objects.all().iterator(chunk_size=500))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during reindexing: {e}"))
            raise e
        
        self.stdout.write(self.style.SUCCESS(f"Reindexed data from {source} to {destination}"))
        
    def swap_alias(self, old_index, new_index):
        """Swap alias — atomic, no downtime.""" 
        
        self.stdout.write(self.style.NOTICE(f"Swapping {old_index} to point to {new_index}..."))
        
        self.es.indices.update_aliases(body={
            "actions": [
                {"remove": {"index": old_index, "alias": ALIAS}},
                {"add":    {"index": new_index, "alias": ALIAS}},
            ]
        })
        
        self.stdout.write(self.style.SUCCESS(f"Swapped alias {ALIAS} to point to {new_index}"))
        
    def delete_index(self, index_name):
        """Delete the old index after alias swap."""
        
        self.stdout.write(self.style.NOTICE(f"Deleting old index {index_name}..."))
        self.es.indices.delete(index=index_name)
        self.stdout.write(self.style.SUCCESS(f"Deleted old index {index_name}"))
        
    def migrate_to_alias(self):
        """Migrate from a single index to an alias pattern."""
        self.stdout.write("First run — migrating to alias pattern...")
        new_index = f"{ALIAS}_v1"
        
        self.create_index(new_index)
        
        self.reindex_data(source=ALIAS, destination=new_index)
        
        self.stdout.write(f"  Deleting original index '{ALIAS}'...")
        self.es.indices.delete(index=ALIAS)
        
        self.es.indices.update_aliases(body={
            "actions": [
                {"add": {"index": new_index, "alias": ALIAS}},
            ]
        })

        self.stdout.write(self.style.SUCCESS(
            f"Migration complete. Alias '{ALIAS}' → {new_index}"
        ))
 
    def reindex(self, current_index):
        """Perform zero-downtime reindexing by creating a new index, reindexing data, swapping the alias, and deleting the old index."""
        
        new_index = self.get_new_index_name(current_index)
        self.stdout.write(f"Current index : {current_index}")
        self.stdout.write(f"New index     : {new_index}")
        self.create_index(new_index)
        self.reindex_data(source=current_index, destination=new_index)
        self.swap_alias(old_index=current_index, new_index=new_index)
        self.delete_index(current_index)