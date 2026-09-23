import structlog
from agents.base_agent import BaseAgent
from google.cloud import bigquery
from config import settings
logger = structlog.get_logger()
# Dataset to BigQuery dataset mapping
DATASET_MAP = {
   "ireland": "KarthikRudrapati",
   "mi": "KarthikRudrapati",
   "germany": "KarthikRudrapati",
   "uk": "KarthikRudrapati",
   "finance": "KarthikRudrapati",
   "customer": "KarthikRudrapati",
}

async def discover_schema(bq_dataset: str) -> dict:
   """Auto-discover all tables and columns from BigQuery dataset."""
   client = bigquery.Client(project=settings.GCP_PROJECT_ID)
   schema = {"tables": {}, "metrics": [], "dimensions": [], "mappings": {}}
   try:
       tables = list(client.list_tables(f"{settings.GCP_PROJECT_ID}.{bq_dataset}"))
       logger.info("Discovered tables", count=len(tables), dataset=bq_dataset)
       for table_ref in tables:
           table_id = table_ref.table_id
           full_table = f"{settings.GCP_PROJECT_ID}.{bq_dataset}.{table_id}"
           table = client.get_table(full_table)
           columns = []
           numeric_cols = []
           date_cols = []
           string_cols = []
           for field in table.schema:
               col = {
                   "name": field.name,
                   "type": field.field_type,
                   "description": field.description or ""
               }
               columns.append(col)
               # Auto-classify columns
               if field.field_type in ("INTEGER", "FLOAT", "NUMERIC", "BIGNUMERIC"):
                   numeric_cols.append(field.name)
                   schema["metrics"].append(field.name)
                   schema["mappings"][field.name.lower()] = f"{full_table}.{field.name}"
               elif field.field_type in ("DATE", "DATETIME", "TIMESTAMP"):
                   date_cols.append(field.name)
                   schema["dimensions"].append(field.name)
               elif field.field_type == "STRING":
                   string_cols.append(field.name)
                   schema["dimensions"].append(field.name)
           schema["tables"][table_id] = {
               "full_name": full_table,
               "columns": columns,
               "numeric_columns": numeric_cols,
               "date_columns": date_cols,
               "string_columns": string_cols,
               "row_count": table.num_rows,
               "date_column": date_cols[0] if date_cols else None,
           }
           logger.info(
               "Table schema discovered",
               table=table_id,
               numeric=numeric_cols,
               dates=date_cols,
               strings=string_cols
           )
       schema["source"] = "bigquery_autodiscovery"
       schema["dataset"] = bq_dataset
       schema["project"] = settings.GCP_PROJECT_ID
   except Exception as e:
       logger.error("Schema discovery failed", error=str(e))
       schema["source"] = "discovery_failed"
       schema["error"] = str(e)
   return schema

class MetadataAgent(BaseAgent):
   agent_id = "metadata"
   label = "Metadata"
   # Cache schema per dataset to avoid repeated BQ calls
   _schema_cache: dict = {}
   async def _execute(self, context: dict) -> dict:
       dataset_id = context.get("dataset_id", "ireland")
       key = dataset_id.lower().replace(" constellation", "").strip()
       bq_dataset = DATASET_MAP.get(key, "KarthikRudrapati")
       # Use cache if available
       if bq_dataset in self._schema_cache:
           logger.info("Using cached schema", dataset=bq_dataset)
           context["metadata"] = self._schema_cache[bq_dataset]
           return context
       # Auto-discover from BigQuery
       logger.info("Discovering schema from BigQuery", dataset=bq_dataset)
       schema = await discover_schema(bq_dataset)
       self._schema_cache[bq_dataset] = schema
       context["metadata"] = schema
       logger.info(
           "Schema discovery complete",
           tables=list(schema.get("tables", {}).keys()),
           metrics=schema.get("metrics", []),
           dimensions=schema.get("dimensions", [])
       )
       return context
