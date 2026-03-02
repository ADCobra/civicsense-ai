# File: src/backend/database.py
"""
Database connection and operations
"""

import os
import asyncpg
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

# Database connection pool (will be initialized at startup)
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool(database_url: str = None, min_size: int = 10, max_size: int = 20):
    """
    Initialize database connection pool
    
    Call this once at application startup
    """
    global _pool
    
    if _pool is not None:
        logger.warning("Database pool already initialized")
        return
    
    db_url = database_url or os.getenv('DATABASE_URL')
    
    if not db_url:
        raise ValueError("DATABASE_URL not provided")
    
    try:
        _pool = await asyncpg.create_pool(
            db_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60
        )
        logger.info(f"✅ Database pool initialized (min={min_size}, max={max_size})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database pool: {e}")
        raise


async def close_db_pool():
    """Close database connection pool"""
    global _pool
    
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


@asynccontextmanager
async def get_db_connection():
    """
    Get a database connection from the pool
    
    Usage:
        async with get_db_connection() as conn:
            result = await conn.fetch("SELECT * FROM opportunities")
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first")
    
    async with _pool.acquire() as connection:
        yield connection


class OpportunityDB:
    """Database operations for opportunities"""
    
    @staticmethod
    async def create(opportunity_data: Dict) -> str:
        """
        Create a new opportunity
        
        Args:
            opportunity_data: Dictionary with opportunity fields
        
        Returns:
            opportunity_id
        """
        async with get_db_connection() as conn:
            # Convert dict to match schema
            query = """
                INSERT INTO opportunities (
                    id, source_id, source_url, title, description, opportunity_type,
                    issuing_authority, authority_level, scheme_code,
                    published_date, application_start, application_end,
                    eligibility, benefit_amount, benefit_description,
                    application_url, required_documents, application_mode,
                    ai_summary, ai_eligibility_explanation, common_mistakes,
                    trust_score, verification_status, translations
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                    $13::jsonb, $14, $15, $16, $17::jsonb, $18,
                    $19, $20::jsonb, $21::jsonb, $22, $23, $24::jsonb
                )
                ON CONFLICT (source_url) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    last_updated = NOW()
                RETURNING id
            """
            
            result = await conn.fetchval(
                query,
                opportunity_data['id'],
                opportunity_data['source_id'],
                opportunity_data['source_url'],
                opportunity_data['title'],
                opportunity_data.get('description'),
                opportunity_data['opportunity_type'],
                opportunity_data.get('issuing_authority'),
                opportunity_data.get('authority_level'),
                opportunity_data.get('scheme_code'),
                opportunity_data['published_date'],
                opportunity_data.get('application_start'),
                opportunity_data.get('application_end'),
                str(opportunity_data.get('eligibility', {})),
                opportunity_data.get('benefit_amount'),
                opportunity_data.get('benefit_description'),
                opportunity_data.get('application_url'),
                str(opportunity_data.get('required_documents', [])),
                opportunity_data.get('application_mode', 'online'),
                opportunity_data.get('ai_summary'),
                str(opportunity_data.get('ai_eligibility_explanation', {})),
                str(opportunity_data.get('common_mistakes', [])),
                opportunity_data.get('trust_score', 0.7),
                opportunity_data.get('verification_status', 'pending'),
                str(opportunity_data.get('translations', {}))
            )
            
            logger.info(f"✅ Created opportunity: {result}")
            return result
    
    @staticmethod
    async def get_by_id(opportunity_id: str) -> Optional[Dict]:
        """Get opportunity by ID"""
        async with get_db_connection() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM opportunities WHERE id = $1",
                opportunity_id
            )
            return dict(result) if result else None
    
    @staticmethod
    async def get_all(
        limit: int = 100,
        offset: int = 0,
        filters: Dict = None
    ) -> List[Dict]:
        """Get all opportunities with optional filters"""
        async with get_db_connection() as conn:
            query = "SELECT * FROM opportunities WHERE 1=1"
            params = []
            param_count = 0
            
            if filters:
                if 'opportunity_type' in filters:
                    param_count += 1
                    query += f" AND opportunity_type = ${param_count}"
                    params.append(filters['opportunity_type'])
                
                if 'verification_status' in filters:
                    param_count += 1
                    query += f" AND verification_status = ${param_count}"
                    params.append(filters['verification_status'])
            
            query += f" ORDER BY published_date DESC LIMIT ${param_count+1} OFFSET ${param_count+2}"
            params.extend([limit, offset])
            
            results = await conn.fetch(query, *params)
            return [dict(row) for row in results]
    
    @staticmethod
    async def update_ai_content(
        opportunity_id: str,
        ai_summary: str = None,
        ai_eligibility_explanation: Dict = None,
        translations: Dict = None
    ):
        """Update AI-generated content"""
        async with get_db_connection() as conn:
            updates = []
            params = []
            param_count = 0
            
            if ai_summary:
                param_count += 1
                updates.append(f"ai_summary = ${param_count}")
                params.append(ai_summary)
            
            if ai_eligibility_explanation:
                param_count += 1
                updates.append(f"ai_eligibility_explanation = ${param_count}::jsonb")
                params.append(str(ai_eligibility_explanation))
            
            if translations:
                param_count += 1
                updates.append(f"translations = ${param_count}::jsonb")
                params.append(str(translations))
            
            if not updates:
                return
            
            param_count += 1
            params.append(opportunity_id)
            
            query = f"""
                UPDATE opportunities
                SET {', '.join(updates)}, last_updated = NOW()
                WHERE id = ${param_count}
            """
            
            await conn.execute(query, *params)
            logger.info(f"✅ Updated AI content for: {opportunity_id}")
    
    @staticmethod
    async def increment_view_count(opportunity_id: str):
        """Increment view counter"""
        async with get_db_connection() as conn:
            await conn.execute(
                "UPDATE opportunities SET view_count = view_count + 1 WHERE id = $1",
                opportunity_id
            )


class SourceDB:
    """Database operations for data sources"""
    
    @staticmethod
    async def get_active_sources() -> List[Dict]:
        """Get all active sources ordered by priority"""
        async with get_db_connection() as conn:
            results = await conn.fetch("""
                SELECT * FROM sources
                WHERE is_active = true
                ORDER BY priority DESC, last_success ASC NULLS FIRST
            """)
            return [dict(row) for row in results]
    
    @staticmethod
    async def update_run_stats(
        source_id: str,
        success: bool,
        items_count: int = 0,
        error_message: str = None
    ):
        """Update source run statistics"""
        async with get_db_connection() as conn:
            if success:
                await conn.execute("""
                    UPDATE sources SET
                        last_run = NOW(),
                        last_success = NOW(),
                        consecutive_failures = 0,
                        total_runs = total_runs + 1,
                        total_successes = total_successes + 1,
                        avg_items_per_run = (
                            (avg_items_per_run * total_successes + $2) / (total_successes + 1)
                        )
                    WHERE id = $1
                """, source_id, items_count)
            else:
                await conn.execute("""
                    UPDATE sources SET
                        last_run = NOW(),
                        consecutive_failures = consecutive_failures + 1,
                        total_runs = total_runs + 1,
                        total_failures = total_failures + 1
                    WHERE id = $1
                """, source_id)
                
                logger.warning(f"Source {source_id} failed: {error_message}")


class RawDataDB:
    """Database operations for raw collected data"""
    
    @staticmethod
    async def store_raw_item(
        source_id: str,
        data: Dict,
        url: str = None,
        collection_log_id: int = None
    ) -> int:
        """Store raw data item before normalization"""
        async with get_db_connection() as conn:
            result = await conn.fetchval("""
                INSERT INTO raw_data (source_id, data, url, collection_log_id)
                VALUES ($1, $2::jsonb, $3, $4)
                RETURNING id
            """, source_id, str(data), url, collection_log_id)
            
            return result
    
    @staticmethod
    async def get_unprocessed(limit: int = 100) -> List[Dict]:
        """Get unprocessed raw data items"""
        async with get_db_connection() as conn:
            results = await conn.fetch("""
                SELECT * FROM raw_data
                WHERE processed = false
                ORDER BY created_at ASC
                LIMIT $1
            """, limit)
            
            return [dict(row) for row in results]
    
    @staticmethod
    async def mark_processed(
        raw_id: int,
        opportunity_id: str = None,
        error: str = None
    ):
        """Mark raw data item as processed"""
        async with get_db_connection() as conn:
            await conn.execute("""
                UPDATE raw_data SET
                    processed = true,
                    processed_at = NOW(),
                    opportunity_id = $2,
                    processing_error = $3
                WHERE id = $1
            """, raw_id, opportunity_id, error)


class CollectionLogDB:
    """Database operations for collection logs"""
    
    @staticmethod
    async def create_log(source_id: str, worker_id: str = None) -> int:
        """Create a new collection log entry"""
        async with get_db_connection() as conn:
            log_id = await conn.fetchval("""
                INSERT INTO collection_logs (source_id, started_at, status, worker_id)
                VALUES ($1, NOW(), 'running', $2)
                RETURNING id
            """, source_id, worker_id)
            
            return log_id
    
    @staticmethod
    async def complete_log(
        log_id: int,
        status: str,
        items_fetched: int = 0,
        items_processed: int = 0,
        items_saved: int = 0,
        items_failed: int = 0,
        error_message: str = None
    ):
        """Complete a collection log"""
        async with get_db_connection() as conn:
            await conn.execute("""
                UPDATE collection_logs SET
                    completed_at = NOW(),
                    duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)),
                    status = $2,
                    items_fetched = $3,
                    items_processed = $4,
                    items_saved = $5,
                    items_failed = $6,
                    error_message = $7
                WHERE id = $1
            """, log_id, status, items_fetched, items_processed,
                 items_saved, items_failed, error_message)