"""
Google Search grounding service with static Ireland fallback.
"""
import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config import settings
logger = structlog.get_logger()
STATIC_IRELAND_CONTEXT = """
Ireland Telecom Market Context (2026):
MARKET SIZE:
- Total mobile subscribers: ~5.2M
- Fixed broadband: ~1.6M households
- Market growth: ~1.8% YoY
- Total telecom revenue: ~3.8B EUR annually
COMPETITOR MARKET SHARE:
- Vodafone Ireland: ~32% (~1.66M subscribers) - market leader, enterprise 5G focus
- Eir: ~28% (~1.46M subscribers) - national fibre infrastructure owner
- Three Ireland: ~22% (~1.14M subscribers) - aggressive pricing, youth segment
- Sky Ireland: ~10% (~520K subscribers) - bundled TV+broadband+mobile
- Virgin Media Ireland: ~8% (~416K) - urban cable stronghold
- MVNOs (GoMo, 48, Tesco Mobile): ~5-6% combined, growing
KEY BENCHMARKS:
- Mobile churn: 15-18% annually
- Fixed broadband churn: 8-12% annually
- Mobile ARPU: 18-22 EUR/month (declining ~2% YoY)
- Fixed ARPU: 45-55 EUR/month
- 5G coverage: 80%+ population
- Fibre coverage: 65% premises
MARKET TRENDS 2026:
- Fixed-mobile convergence: bundle adoption +12% YoY
- 5G enterprise services growing (IoT, private networks)
- ARPU pressure from MVNO budget operators
- OTT substitution reducing voice revenue ~8% YoY
- Mobile data consumption up 35% YoY
- eSIM adoption accelerating switching
- ComReg oversight on wholesale access pricing
COMPETITIVE DYNAMICS:
- Sky and Virgin Media aggressive bundle pricing
- Three Ireland investing in 5G standalone network
- Eir GoMo MVNO disrupting budget segment
- Vodafone leading enterprise 5G and IoT contracts
- Churn battleground: retention offers and loyalty programmes
"""

async def get_ireland_market_context() -> str:
   """
   Try Google Search grounding — fall back to static context if unavailable.
   """
   vertexai.init(
       project=settings.GCP_PROJECT_ID,
       location=settings.GCP_LOCATION
   )
   search_prompt = (
       "Ireland telecom market 2026 Vodafone Ireland Eir Three Ireland "
       "subscriber numbers market share churn ARPU 5G latest statistics"
   )
   gen_config = GenerationConfig(temperature=0.1, max_output_tokens=1024)
   # Attempt 1
   try:
       from vertexai.generative_models import Tool, grounding
       model = GenerativeModel(
           model_name=settings.VERTEX_AI_MODEL,
           tools=[Tool.from_google_search_retrieval(
               grounding.GoogleSearchRetrieval()
           )],
       )
       resp = await model.generate_content_async(search_prompt, generation_config=gen_config)
       logger.info("Google Search grounding success: attempt 1")
       return resp.text
   except Exception as e:
       logger.warning("Search attempt 1 failed", error=str(e)[:80])
   # Attempt 2
   try:
       from vertexai.preview.generative_models import (
           GenerativeModel as PM, Tool, grounding
       )
       model = PM(
           model_name=settings.VERTEX_AI_MODEL,
           tools=[Tool.from_google_search_retrieval(
               grounding.GoogleSearchRetrieval()
           )],
       )
       resp = await model.generate_content_async(search_prompt, generation_config=gen_config)
       logger.info("Google Search grounding success: attempt 2")
       return resp.text
   except Exception as e:
       logger.warning("Search attempt 2 failed", error=str(e)[:80])
   # Attempt 3
   try:
       model = GenerativeModel(model_name=settings.VERTEX_AI_MODEL)
       resp = await model.generate_content_async(
           search_prompt,
           tools=[{"google_search_retrieval": {}}],
           generation_config=gen_config,
       )
       logger.info("Google Search grounding success: attempt 3")
       return resp.text
   except Exception as e:
       logger.warning("Search attempt 3 failed", error=str(e)[:80])
   logger.info("All search attempts failed — using static Ireland context")
   return STATIC_IRELAND_CONTEXT
