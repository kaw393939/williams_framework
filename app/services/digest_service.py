"""
DigestService - Daily digest generation and email delivery.

This service manages the creation and delivery of daily email digests
containing curated high-quality content from the library.
"""
from datetime import datetime, timedelta
from typing import Optional
import json

from app.core.models import DigestItem, Digest
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.redis_repository import RedisRepository


# Constants
DEFAULT_MIN_QUALITY = 7.0
DEFAULT_DAYS_BACK = 7
DEFAULT_LIMIT = 10
MAX_RECORDS_TO_QUERY = 1000

# Email configuration
SMTP_HOST = 'localhost'
SMTP_PORT = 1025
DEFAULT_FROM_EMAIL = 'digest@librarian.ai'

# Tier colors for HTML rendering
TIER_COLORS = {
    'tier-a': '#10b981',  # green
    'tier-b': '#3b82f6',  # blue
    'tier-c': '#f59e0b',  # amber
    'tier-d': '#6b7280'   # gray
}


class DigestService:
    """
    Service for generating and delivering daily content digests.
    
    Handles:
    - Selecting content for digests
    - Generating HTML and text email formats
    - Sending emails via SMTP
    - Tracking digest history
    """
    
    def __init__(
        self,
        postgres_repo: PostgresRepository,
        redis_repo: RedisRepository
    ):
        """
        Initialize DigestService with repositories.
        
        Args:
            postgres_repo: PostgreSQL repository for metadata
            redis_repo: Redis repository for caching
        """
        self.postgres_repo = postgres_repo
        self.redis_repo = redis_repo
    
    @staticmethod
    def _parse_metadata(metadata: dict | str) -> dict:
        """
        Parse metadata from database (may be string or dict).
        
        Args:
            metadata: Metadata from database
            
        Returns:
            Parsed metadata dictionary
        """
        if isinstance(metadata, str):
            return json.loads(metadata)
        return metadata
    
    @staticmethod
    def _format_tags_html(tags: list[str]) -> str:
        """
        Format tags as HTML spans.
        
        Args:
            tags: List of tag strings
            
        Returns:
            HTML string with styled tags
        """
        return ' '.join([
            f'<span style="background-color: #e5e7eb; padding: 2px 8px; '
            f'border-radius: 3px; font-size: 12px; color: #4b5563;">{tag}</span>'
            for tag in tags
        ])
    
    @staticmethod
    def _render_digest_item_html(item: DigestItem) -> str:
        """
        Render a single digest item as HTML.
        
        Args:
            item: DigestItem to render
            
        Returns:
            HTML string for the item
        """
        tier_color = TIER_COLORS.get(item.tier, TIER_COLORS['tier-d'])
        tags_html = DigestService._format_tags_html(item.tags)
        
        return f'''
        <div style="margin-bottom: 30px; padding: 20px; background-color: #f9fafb; border-left: 4px solid {tier_color}; border-radius: 4px;">
            <h2 style="margin: 0 0 10px 0; font-size: 18px;">
                <a href="{item.url}" style="color: #1f2937; text-decoration: none;">{item.title}</a>
            </h2>
            <div style="margin-bottom: 10px;">
                <span style="background-color: {tier_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                    {item.tier.upper()} • {item.quality_score:.1f}/10
                </span>
            </div>
            <p style="margin: 10px 0; color: #4b5563; line-height: 1.6;">{item.summary}</p>
            <div style="margin-top: 10px;">
                {tags_html}
            </div>
        </div>
        '''
    
    async def select_content_for_digest(
        self,
        date: datetime,
        min_quality: float = DEFAULT_MIN_QUALITY,
        days_back: int = DEFAULT_DAYS_BACK,
        preferred_tiers: Optional[list[str]] = None,
        limit: int = DEFAULT_LIMIT
    ) -> list[DigestItem]:
        """
        Select content for digest based on criteria.
        
        Queries the library for recent high-quality content and filters based on:
        - Quality score threshold (default: 7.0/10)
        - Date range (default: last 7 days)
        - Tier preferences (optional: tier-a, tier-b, tier-c, tier-d)
        
        Args:
            date: Digest date
            min_quality: Minimum quality score (0-10 scale)
            days_back: How many days back to look for content
            preferred_tiers: List of preferred tiers to include
            limit: Maximum items to return
            
        Returns:
            List of DigestItem objects, sorted by quality score (highest first)
        """
        # Calculate date range
        start_date = date - timedelta(days=days_back)
        
        # Query processing records for library content
        records = await self.postgres_repo.list_processing_records(
            operation='add_to_library',
            status='completed',
            limit=MAX_RECORDS_TO_QUERY
        )
        
        # Filter and convert to DigestItem
        items = []
        for record in records:
            metadata = self._parse_metadata(record['metadata'])
            
            # Extract data
            quality_score = metadata.get('quality_score', 0.0)
            tier = metadata.get('tier', 'tier-d')
            added_date = record['started_at']
            
            # Apply filters
            if quality_score < min_quality:
                continue
            if added_date < start_date:
                continue
            if preferred_tiers and tier not in preferred_tiers:
                continue
            
            # Create DigestItem
            item = DigestItem(
                url=record['content_url'],
                title=metadata.get('title', 'Untitled'),
                summary=metadata.get('summary', ''),
                quality_score=quality_score,
                tier=tier,
                tags=metadata.get('tags', []),
                added_date=added_date
            )
            items.append(item)
        
        # Sort by quality (highest first) and limit
        items.sort(key=lambda x: x.quality_score, reverse=True)
        return items[:limit]
    
    async def generate_digest_html(
        self,
        items: list[DigestItem],
        date: datetime,
        subject: str
    ) -> str:
        """
        Generate HTML email content for digest.
        
        Creates a professional, styled HTML email with:
        - Header with subject, date, and item count
        - Individual items with quality badges and tier colors
        - Tags and summaries for each item
        - Footer with unsubscribe links
        
        Args:
            items: Digest items to include
            date: Digest date for display
            subject: Email subject line
            
        Returns:
            Complete HTML document as string
        """
        # Build items HTML using helper method
        items_html = ""
        for item in items:
            items_html += self._render_digest_item_html(item)
        
        # Build complete HTML
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #1f2937; color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">{subject}</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{date.strftime('%B %d, %Y')}</p>
                <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 14px;">{len(items)} curated articles</p>
            </div>
            
            <div style="padding: 30px; background-color: white;">
                {items_html if items else '<p style="text-align: center; color: #6b7280;">No new content available for this digest.</p>'}
            </div>
            
            <div style="background-color: #f3f4f6; padding: 20px; border-radius: 0 0 8px 8px; text-align: center; font-size: 12px; color: #6b7280;">
                <p style="margin: 0;">You're receiving this because you subscribed to our daily digest.</p>
                <p style="margin: 10px 0 0 0;">
                    <a href="#" style="color: #3b82f6; text-decoration: none;">Unsubscribe</a> • 
                    <a href="#" style="color: #3b82f6; text-decoration: none;">Preferences</a>
                </p>
            </div>
        </body>
        </html>
        '''
        
        return html
    
    async def generate_digest_text(
        self,
        items: list[DigestItem],
        date: datetime,
        subject: str
    ) -> str:
        """
        Generate plain text email content for digest.
        
        Creates a plain text version of the digest for email clients that
        don't support HTML, or as a fallback. Includes all the same information
        as the HTML version in a readable text format.
        
        Args:
            items: Digest items to include
            date: Digest date for display  
            subject: Email subject line
            
        Returns:
            Plain text document as string
        """
        # Build header
        text = f"""
{'=' * 70}
{subject}
{date.strftime('%B %d, %Y')}
{len(items)} curated articles
{'=' * 70}

"""
        
        # Add items
        if items:
            for i, item in enumerate(items, 1):
                tags_str = ', '.join(item.tags)
                text += f"""
{i}. {item.title}
   {item.tier.upper()} • Quality: {item.quality_score:.1f}/10
   
   {item.summary}
   
   Link: {item.url}
   Tags: {tags_str}
   
{'-' * 70}

"""
        else:
            text += "No content available for this digest.\n\n"
        
        # Add footer
        text += f"""
{'=' * 70}
You're receiving this because you subscribed to our daily digest.
To unsubscribe or manage preferences, visit: [preferences link]
{'=' * 70}
"""
        
        return text
    
    async def send_digest_email(self, digest: Digest) -> bool:
        """
        Send digest via SMTP.
        
        Creates a multipart MIME message with both HTML and plain text versions,
        then sends via SMTP. In production, configure SMTP_HOST and SMTP_PORT
        environment variables for your mail server.
        
        Args:
            digest: Digest object containing subject, recipients, and content
            
        Returns:
            True if sent successfully, False if any error occurred
        """
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            # Create multipart message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = digest.subject
            msg['From'] = DEFAULT_FROM_EMAIL
            msg['To'] = ', '.join(digest.recipients)
            
            # Attach plain text and HTML versions
            if digest.text_content:
                text_part = MIMEText(digest.text_content, 'plain')
                msg.attach(text_part)
            
            if digest.html_content:
                html_part = MIMEText(digest.html_content, 'html')
                msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            # Log error and return False
            print(f"Failed to send digest: {e}")
            return False
    
    async def mark_digest_as_sent(
        self,
        digest_id: str,
        recipients: list[str],
        items_count: int
    ) -> None:
        """
        Mark digest as sent in database.
        
        Args:
            digest_id: Digest identifier
            recipients: Email recipients
            items_count: Number of items in digest
        """
        # Create processing record
        await self.postgres_repo.create_processing_record(
            record_id=digest_id,
            content_url=f"digest_{digest_id}",
            operation='send_digest',
            status='completed',
            metadata=json.dumps({
                'digest_id': digest_id,
                'recipients': recipients,
                'items_count': items_count,
                'sent_at': datetime.now().isoformat()
            })
        )
    
    async def get_digest_history(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> list[Digest]:
        """
        Retrieve digest history.
        
        Args:
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of Digest objects
        """
        # Query processing records for digests with pagination
        query = """
            SELECT * FROM processing_records 
            WHERE operation = 'send_digest' AND status = 'completed'
            ORDER BY started_at DESC
            LIMIT $1 OFFSET $2
        """
        records = await self.postgres_repo.fetch_all(query, limit, offset)
        
        # Convert to Digest objects
        digests = []
        for record in records:
            metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
            
            digest = Digest(
                digest_id=metadata.get('digest_id', record['record_id']),
                date=record['started_at'],
                subject=f"Daily Digest - {record['started_at'].strftime('%B %d, %Y')}",
                items=[],  # Not storing full items in history
                html_content=None,
                text_content=None,
                recipients=metadata.get('recipients', []),
                sent_at=datetime.fromisoformat(metadata['sent_at']) if 'sent_at' in metadata else record['started_at'],
                created_at=record['started_at']
            )
            digests.append(digest)
        
        return digests
