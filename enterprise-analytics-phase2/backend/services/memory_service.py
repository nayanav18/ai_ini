"""Persistent conversation memory backed by BigQuery."""
import json
import uuid
from datetime import datetime

import structlog

logger = structlog.get_logger()

try:
    from google.cloud import bigquery
    from config import settings

    PROJECT = settings.GCP_PROJECT_ID
    DATASET = settings.BIGQUERY_DATASET
    BQ_USERS = f"`{PROJECT}.{DATASET}.analytics_users`"
    BQ_CONVS = f"`{PROJECT}.{DATASET}.analytics_conversations`"
    BQ_MSGS = f"`{PROJECT}.{DATASET}.analytics_messages`"
    BQ_ENABLED = True

    def _client():
        return bigquery.Client(project=PROJECT, location=settings.BIGQUERY_LOCATION)

except Exception as exc:  # pragma: no cover - depends on runtime environment
    BQ_ENABLED = False
    logger.warning("BQ memory service disabled", error=str(exc)[:120])


async def ensure_tables_exist():
    """Create memory tables if they do not already exist."""
    if not BQ_ENABLED:
        return

    statements = [
        f"""CREATE TABLE IF NOT EXISTS {BQ_USERS} (
            user_id STRING NOT NULL,
            persona_id STRING DEFAULT 'analyst',
            display_name STRING,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )""",
        f"""CREATE TABLE IF NOT EXISTS {BQ_CONVS} (
            conversation_id STRING NOT NULL,
            user_id STRING NOT NULL,
            persona_id STRING DEFAULT 'analyst',
            dataset_id STRING DEFAULT 'ireland',
            title STRING,
            message_count INT64 DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )""",
        f"""CREATE TABLE IF NOT EXISTS {BQ_MSGS} (
            message_id STRING NOT NULL,
            conversation_id STRING NOT NULL,
            user_id STRING NOT NULL,
            role STRING NOT NULL,
            query STRING,
            content JSON,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )""",
    ]

    client = _client()
    for sql in statements:
        try:
            client.query(sql).result()
        except Exception as exc:
            logger.warning("Memory table create skipped", error=str(exc)[:120])
    logger.info("Memory tables ready")


async def upsert_user(user_id: str, persona_id: str = "analyst") -> None:
    if not BQ_ENABLED:
        return
    try:
        client = _client()
        sql = f"""
        MERGE {BQ_USERS} T
        USING (SELECT @uid AS user_id, @pid AS persona_id) S
        ON T.user_id = S.user_id
        WHEN MATCHED THEN UPDATE SET
            persona_id = S.persona_id,
            last_active = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT
            (user_id, persona_id, created_at, last_active)
        VALUES
            (S.user_id, S.persona_id, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("uid", "STRING", user_id),
            bigquery.ScalarQueryParameter("pid", "STRING", persona_id),
        ])
        client.query(sql, job_config=cfg).result()
    except Exception as exc:
        logger.warning("upsert_user failed", error=str(exc)[:120])


async def get_user_persona(user_id: str) -> str:
    if not BQ_ENABLED:
        return "analyst"
    try:
        client = _client()
        sql = f"SELECT persona_id FROM {BQ_USERS} WHERE user_id = @uid LIMIT 1"
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("uid", "STRING", user_id)
        ])
        rows = list(client.query(sql, job_config=cfg).result())
        return rows[0]["persona_id"] if rows else "analyst"
    except Exception as exc:
        logger.warning("get_user_persona failed", error=str(exc)[:120])
        return "analyst"


async def create_conversation(
    user_id: str,
    persona_id: str = "analyst",
    dataset_id: str = "ireland",
    title: str = "New Conversation",
    conversation_id: str | None = None,
) -> str:
    """Create a conversation. A supplied ID is preserved for frontend continuity."""
    conv_id = conversation_id or str(uuid.uuid4())
    if not BQ_ENABLED:
        return conv_id

    try:
        client = _client()
        sql = f"""
        INSERT INTO {BQ_CONVS}
          (conversation_id, user_id, persona_id, dataset_id,
           title, message_count, created_at, updated_at)
        VALUES
          (@cid, @uid, @pid, @did, @title, 0,
           CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("cid", "STRING", conv_id),
            bigquery.ScalarQueryParameter("uid", "STRING", user_id),
            bigquery.ScalarQueryParameter("pid", "STRING", persona_id),
            bigquery.ScalarQueryParameter("did", "STRING", dataset_id),
            bigquery.ScalarQueryParameter("title", "STRING", title[:120]),
        ])
        client.query(sql, job_config=cfg).result()
        logger.info("Conversation created", conversation_id=conv_id, user_id=user_id)
    except Exception as exc:
        logger.warning("create_conversation failed", error=str(exc)[:120])
    return conv_id


async def ensure_conversation(
    conversation_id: str,
    user_id: str,
    persona_id: str = "analyst",
    dataset_id: str = "ireland",
    title: str = "New Conversation",
) -> str:
    """Ensure an ID belongs to the current user; create it when missing."""
    if not BQ_ENABLED:
        return conversation_id

    try:
        client = _client()
        check_sql = f"""
        SELECT conversation_id
        FROM {BQ_CONVS}
        WHERE conversation_id = @cid AND user_id = @uid
        LIMIT 1
        """
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("cid", "STRING", conversation_id),
            bigquery.ScalarQueryParameter("uid", "STRING", user_id),
        ])
        if list(client.query(check_sql, job_config=cfg).result()):
            return conversation_id

        # Never attach a conversation belonging to another user.
        owner_sql = f"SELECT user_id FROM {BQ_CONVS} WHERE conversation_id = @cid LIMIT 1"
        owner_cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("cid", "STRING", conversation_id)
        ])
        if list(client.query(owner_sql, job_config=owner_cfg).result()):
            return str(uuid.uuid4())

        return await create_conversation(
            user_id=user_id,
            persona_id=persona_id,
            dataset_id=dataset_id,
            title=title,
            conversation_id=conversation_id,
        )
    except Exception as exc:
        logger.warning("ensure_conversation failed", error=str(exc)[:120])
        return conversation_id


async def update_conversation_title(
    conversation_id: str,
    user_id: str,
    title: str,
) -> bool:
    if not BQ_ENABLED:
        return False
    try:
        client = _client()
        sql = f"""
        UPDATE {BQ_CONVS}
        SET title = @title, updated_at = CURRENT_TIMESTAMP()
        WHERE conversation_id = @cid AND user_id = @uid
        """
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("title", "STRING", title[:120]),
            bigquery.ScalarQueryParameter("cid", "STRING", conversation_id),
            bigquery.ScalarQueryParameter("uid", "STRING", user_id),
        ])
        job = client.query(sql, job_config=cfg)
        job.result()
        return True
    except Exception as exc:
        logger.warning("update_conversation_title failed", error=str(exc)[:120])
        return False


async def load_conversations(user_id: str, limit: int = 50) -> list:
    if not BQ_ENABLED:
        return []
    try:
        client = _client()
        sql = f"""
        SELECT conversation_id, user_id, persona_id, dataset_id,
               title, message_count, created_at, updated_at
        FROM {BQ_CONVS}
        WHERE user_id = @uid
        ORDER BY updated_at DESC
        LIMIT @lim
        """
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("uid", "STRING", user_id),
            bigquery.ScalarQueryParameter("lim", "INT64", limit),
        ])
        return [dict(row) for row in client.query(sql, job_config=cfg).result()]
    except Exception as exc:
        logger.warning("load_conversations failed", error=str(exc)[:120])
        return []


async def save_message(
    conversation_id: str,
    user_id: str,
    role: str,
    query: str,
    content: dict | None = None,
) -> str:
    msg_id = str(uuid.uuid4())
    if not BQ_ENABLED:
        return msg_id

    try:
        client = _client()
        content_json = json.dumps(content or {}, default=str)
        sql = f"""
        INSERT INTO {BQ_MSGS}
          (message_id, conversation_id, user_id, role, query, content, generated_at)
        VALUES
          (@mid, @cid, @uid, @role, @query, PARSE_JSON(@content), CURRENT_TIMESTAMP())
        """
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("mid", "STRING", msg_id),
            bigquery.ScalarQueryParameter("cid", "STRING", conversation_id),
            bigquery.ScalarQueryParameter("uid", "STRING", user_id),
            bigquery.ScalarQueryParameter("role", "STRING", role),
            bigquery.ScalarQueryParameter("query", "STRING", query[:2000]),
            bigquery.ScalarQueryParameter("content", "STRING", content_json),
        ])
        client.query(sql, job_config=cfg).result()

        update_sql = f"""
        UPDATE {BQ_CONVS}
        SET message_count = message_count + 1,
            updated_at = CURRENT_TIMESTAMP()
        WHERE conversation_id = @cid AND user_id = @uid
        """
        update_cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("cid", "STRING", conversation_id),
            bigquery.ScalarQueryParameter("uid", "STRING", user_id),
        ])
        client.query(update_sql, job_config=update_cfg).result()
    except Exception as exc:
        logger.warning("save_message failed", error=str(exc)[:120])
    return msg_id


async def load_messages(
    conversation_id: str,
    limit: int = 100,
    user_id: str | None = None,
) -> list:
    if not BQ_ENABLED:
        return []
    try:
        client = _client()
        where = ["conversation_id = @cid"]
        params = [bigquery.ScalarQueryParameter("cid", "STRING", conversation_id)]
        if user_id:
            where.append("user_id = @uid")
            params.append(bigquery.ScalarQueryParameter("uid", "STRING", user_id))

        sql = f"""
        SELECT message_id, conversation_id, user_id, role, query,
               TO_JSON_STRING(content) AS content_json, generated_at
        FROM {BQ_MSGS}
        WHERE {' AND '.join(where)}
        ORDER BY generated_at DESC
        LIMIT @lim
        """
        params.append(bigquery.ScalarQueryParameter("lim", "INT64", limit))
        rows = list(client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())

        messages = []
        for row in reversed(rows):
            try:
                content = json.loads(row["content_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                content = {"text": row["query"] or ""}
            messages.append({
                "message_id": row["message_id"],
                "conversation_id": row["conversation_id"],
                "user_id": row["user_id"],
                "role": row["role"],
                "query": row["query"] or "",
                "content": content,
                "generated_at": row["generated_at"].isoformat() if hasattr(row["generated_at"], "isoformat") else str(row["generated_at"]),
            })
        return messages
    except Exception as exc:
        logger.warning("load_messages failed", error=str(exc)[:120])
        return []


def build_context_string(messages: list, max_chars: int = 2000) -> str:
    if not messages:
        return ""
    lines = ["PREVIOUS CONVERSATION CONTEXT:"]
    total = 0
    for msg in reversed(messages[-10:]):
        prefix = "User" if msg.get("role") == "user" else "AI"
        content = msg.get("content")
        if isinstance(content, dict) and content.get("text"):
            text = content["text"]
        elif isinstance(content, str):
            text = content
        else:
            text = msg.get("query", "")
        line = f"  {prefix}: {str(text)[:300]}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    lines.append("Use this context only when the user references previous queries.")
    return "\n".join(lines)
