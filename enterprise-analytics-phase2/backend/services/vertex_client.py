import json
import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config import settings
logger = structlog.get_logger()
_model: GenerativeModel | None = None

def init_vertex_ai():
   global _model
   vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
   _model = GenerativeModel(model_name=settings.VERTEX_AI_MODEL)
logger.info("Vertex AI initialised", model=settings.VERTEX_AI_MODEL)

def get_model() -> GenerativeModel:
   if _model is None:
       raise RuntimeError("Vertex AI not initialised")
   return _model

async def generate_analytics(system_prompt: str, history: list, user_query: str) -> dict:
   model = get_model()
   # Build contents with system prompt prepended to first user message
   contents = []
   for msg in history:
       role = "user" if msg["role"] == "user" else "model"
       contents.append({"role": role, "parts": [{"text": msg["content"]}]})
   # Combine system prompt + user query
   full_query = f"{system_prompt}\n\nUser Query: {user_query}"
   contents.append({"role": "user", "parts": [{"text": full_query}]})
   try:
       response = await model.generate_content_async(
           contents,
           generation_config=GenerationConfig(
               temperature=settings.VERTEX_AI_TEMPERATURE,
               max_output_tokens=settings.VERTEX_AI_MAX_TOKENS,
           ),
       )
       raw = response.text.strip()
       if raw.startswith("```"):
           raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
       return json.loads(raw)
   except json.JSONDecodeError as e:
       logger.error("JSON parse error", error=str(e))
       return {"error": "Invalid JSON from model"}
   except Exception as e:
       logger.error("Vertex AI error", error=str(e))
       raise
