"""
Database consistency cleanup script.

Checks and removes inconsistent data across all four tables:
    users, conversations, messages, query_estimations

Usage:
    # Preview only – no changes made
    uv run python cleanup_db.py --dry-run

    # Apply all fixes
    uv run python cleanup_db.py
"""

import argparse
import asyncio
import logging
import os
import sys

# Ensure the app package is importable when running from backend/
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import async_session_factory, DATABASE_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

VALID_ROLES = {"user", "assistant", "system"}


# ---------------------------------------------------------------------------
# Individual audit/fix functions
# ---------------------------------------------------------------------------


async def audit_incomplete_messages(session: AsyncSession, dry_run: bool) -> int:
    """Messages where streaming was interrupted (is_complete = FALSE)."""
    result = await session.execute(
        text("SELECT COUNT(*) FROM messages WHERE is_complete = FALSE")
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text("DELETE FROM messages WHERE is_complete = FALSE")
        )
        logger.info(f"  deleted {count} incomplete message(s)")
    return count


async def audit_invalid_role_messages(session: AsyncSession, dry_run: bool) -> int:
    """Messages with a role value outside ('user', 'assistant', 'system')."""
    result = await session.execute(
        text("SELECT COUNT(*) FROM messages WHERE role NOT IN ('user', 'assistant', 'system')")
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text("DELETE FROM messages WHERE role NOT IN ('user', 'assistant', 'system')")
        )
        logger.info(f"  deleted {count} message(s) with invalid role")
    return count


async def audit_empty_content_messages(session: AsyncSession, dry_run: bool) -> int:
    """Messages with an empty string content."""
    result = await session.execute(
        text("SELECT COUNT(*) FROM messages WHERE content = ''")
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text("DELETE FROM messages WHERE content = ''")
        )
        logger.info(f"  deleted {count} message(s) with empty content")
    return count


async def audit_dangling_estimation_fk(session: AsyncSession, dry_run: bool) -> int:
    """Messages where estimation_id → query_estimations reference is broken."""
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM messages m
            WHERE m.estimation_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM query_estimations qe
                  WHERE qe.id = m.estimation_id
              )
            """
        )
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text(
                """
                UPDATE messages SET estimation_id = NULL
                WHERE estimation_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM query_estimations qe
                      WHERE qe.id = estimation_id
                  )
                """
            )
        )
        logger.info(f"  nulled estimation_id in {count} message(s) with dangling FK")
    return count


async def audit_messages_in_soft_deleted_conversations(
    session: AsyncSession, dry_run: bool
) -> int:
    """Messages that belong to soft-deleted conversations."""
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.deleted_at IS NOT NULL
            """
        )
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text(
                """
                DELETE FROM messages
                WHERE conversation_id IN (
                    SELECT id FROM conversations WHERE deleted_at IS NOT NULL
                )
                """
            )
        )
        logger.info(f"  deleted {count} message(s) in soft-deleted conversations")
    return count


async def audit_soft_deleted_conversations(session: AsyncSession, dry_run: bool) -> int:
    """Hard-delete conversations that were soft-deleted (messages already removed above)."""
    result = await session.execute(
        text("SELECT COUNT(*) FROM conversations WHERE deleted_at IS NOT NULL")
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text("DELETE FROM conversations WHERE deleted_at IS NOT NULL")
        )
        logger.info(f"  hard-deleted {count} soft-deleted conversation(s)")
    return count


async def audit_dangling_user_fk_in_conversations(
    session: AsyncSession, dry_run: bool
) -> int:
    """Conversations where user_id → users reference is broken."""
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM conversations c
            WHERE c.user_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM users u WHERE u.id = c.user_id
              )
            """
        )
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text(
                """
                UPDATE conversations SET user_id = NULL
                WHERE user_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM users u WHERE u.id = user_id
                  )
                """
            )
        )
        logger.info(f"  nulled user_id in {count} conversation(s) with dangling FK")
    return count


async def audit_empty_conversations(session: AsyncSession, dry_run: bool) -> int:
    """Conversations with no messages at all (never used or fully emptied by prior steps)."""
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM conversations c
            WHERE c.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM messages m WHERE m.conversation_id = c.id
              )
            """
        )
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text(
                """
                DELETE FROM conversations
                WHERE deleted_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM messages m
                      WHERE m.conversation_id = conversations.id
                  )
                """
            )
        )
        logger.info(f"  deleted {count} empty conversation(s)")
    return count


async def audit_orphaned_query_estimations(session: AsyncSession, dry_run: bool) -> int:
    """query_estimations not referenced by any messages.estimation_id."""
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM query_estimations qe
            WHERE NOT EXISTS (
                SELECT 1 FROM messages m WHERE m.estimation_id = qe.id
            )
            """
        )
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text(
                """
                DELETE FROM query_estimations
                WHERE NOT EXISTS (
                    SELECT 1 FROM messages m
                    WHERE m.estimation_id = query_estimations.id
                )
                """
            )
        )
        logger.info(f"  deleted {count} orphaned query_estimation(s)")
    return count


async def audit_out_of_range_confidence(session: AsyncSession, dry_run: bool) -> int:
    """query_estimations where confidence_score is outside [0.0, 1.0]. Clamp in place."""
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM query_estimations
            WHERE confidence_score < 0.0 OR confidence_score > 1.0
            """
        )
    )
    count: int = result.scalar_one()
    if count and not dry_run:
        await session.execute(
            text(
                """
                UPDATE query_estimations
                SET confidence_score = GREATEST(0.0, LEAST(1.0, confidence_score))
                WHERE confidence_score < 0.0 OR confidence_score > 1.0
                """
            )
        )
        logger.info(f"  clamped confidence_score in {count} query_estimation(s)")
    return count


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


CHECKS = [
    # (label, function)
    # Order matters: messages in soft-deleted convos must go before the convos themselves,
    # dangling FK fix in messages must come before messages are deleted, etc.
    ("incomplete messages (is_complete=False)", audit_incomplete_messages),
    ("messages with invalid role", audit_invalid_role_messages),
    ("messages with empty content", audit_empty_content_messages),
    ("messages with dangling estimation_id FK", audit_dangling_estimation_fk),
    ("messages in soft-deleted conversations", audit_messages_in_soft_deleted_conversations),
    ("soft-deleted conversations (hard delete)", audit_soft_deleted_conversations),
    ("conversations with dangling user_id FK", audit_dangling_user_fk_in_conversations),
    ("empty conversations (no messages)", audit_empty_conversations),
    ("orphaned query_estimations", audit_orphaned_query_estimations),
    ("query_estimations with out-of-range confidence_score", audit_out_of_range_confidence),
]


async def run_cleanup(dry_run: bool) -> None:
    mode = "DRY-RUN (no changes)" if dry_run else "APPLY (modifying database)"
    db_host = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    logger.info(f"Mode  : {mode}")
    logger.info(f"DB    : {db_host}")
    logger.info("-" * 60)

    summary: dict[str, int] = {}

    # Each check runs in its own transaction so that subsequent FK constraint
    # checks (and orphan subqueries) see the fully committed state of prior
    # steps.  asyncpg's FK checks do not see in-transaction uncommitted deletes
    # made by previous statements, so committing between steps is required.
    for label, fn in CHECKS:
        async with async_session_factory() as session:
            count = await fn(session, dry_run)
            if not dry_run:
                await session.commit()
            summary[label] = count
        status = "⚠" if count else "✓"
        logger.info(f"  {status}  [{count:>6}]  {label}")

    logger.info("-" * 60)
    if not dry_run:
        logger.info("All changes committed.")
    total = sum(summary.values())
    logger.info(f"Total inconsistencies {'found' if dry_run else 'fixed'}: {total}")
    if dry_run and total:
        logger.info("Re-run without --dry-run to apply fixes.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check and clean inconsistent data in the GEO Survival Analysis database."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print counts of inconsistent rows without modifying the database.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_cleanup(dry_run=args.dry_run))
