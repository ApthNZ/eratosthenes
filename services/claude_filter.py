"""Claude AI filtering service for RSS feed items."""
import logging
import os
import json
from typing import List, Dict
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


class ClaudeFilter:
    """Filter RSS feed items using Claude AI."""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def filter_relevance(self, items: List[Dict]) -> List[Dict]:
        """Filter items for InfoSec relevance (Pass 1).
        
        Processes items in batches of 10 for cost efficiency.
        
        Args:
            items: List of feed items to filter
            
        Returns:
            List of items with is_relevant and reasoning fields added
        """
        batch_size = 10
        filtered_items = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            try:
                results = await self._filter_batch(batch)
                filtered_items.extend(results)
            except Exception as e:
                logger.error(f"Failed to filter batch: {e}")
                # Mark all items as not relevant if filtering fails
                for item in batch:
                    item['is_relevant'] = False
                    item['reasoning'] = f"Filter error: {str(e)}"
                filtered_items.extend(batch)

        return filtered_items

    async def _filter_batch(self, items: List[Dict]) -> List[Dict]:
        """Filter a batch of items for relevance."""
        # Build prompt with all items in batch
        items_text = ""
        for idx, item in enumerate(items, 1):
            # Truncate content to avoid token limits
            content = item.get('content', '')[:500]
            if not content:
                content = item.get('summary', '')[:500]

            items_text += f"\n## Item {idx}\n"
            items_text += f"Title: {item['title']}\n"
            items_text += f"Content: {content}\n"

        prompt = f"""You are filtering RSS feed items for a Security Operations Center (SOC) analyst.

Evaluate each item below and determine if it is directly relevant to information security / cybersecurity.

INCLUDE items about:
- Vulnerabilities, exploits, CVEs
- Data breaches, incidents, threat actors
- Security tools, techniques, defensive measures
- Malware, ransomware, attack campaigns
- Security research and analysis

EXCLUDE items about:
- Marketing content (product launches, webinars, ebooks)
- General business/tech news not related to security
- Opinion pieces without technical substance
- Job postings, company announcements
- Conference advertisements

{items_text}

Respond with a JSON array where each element corresponds to an item (in order) with this structure:
{{
  "is_relevant": true/false,
  "reasoning": "brief explanation"
}}

Only return the JSON array, nothing else."""

        # Call Claude
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('\n', 1)[1]
            response_text = response_text.rsplit('```', 1)[0]

        results = json.loads(response_text)

        # Add results to items
        for item, result in zip(items, results):
            item['is_relevant'] = result['is_relevant']
            item['reasoning'] = result['reasoning']

        return items
