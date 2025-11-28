import json
import logging
import os
from typing import List, Dict, Optional, Tuple
import yaml
import asyncio
from datetime import datetime

import anthropic
from anthropic import AsyncAnthropic

from models.feed_item import FeedItem

logger = logging.getLogger(__name__)

class ClaudeFilter:
    """Service for filtering feed items using Claude API."""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.priority_criteria = self._load_priority_criteria()
    
    def _load_priority_criteria(self) -> Dict:
        """Load priority criteria from YAML config."""
        try:
            with open("config/priority_criteria.yaml", "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("Priority criteria config not found, using defaults")
            return {
                "priority_criteria": {
                    "critical_vendors": ["Microsoft", "Cisco", "VMware"],
                    "breach_indicators": ["million users", "ransomware", "data breach"],
                    "severity_keywords": ["critical vulnerability", "zero-day", "actively exploited"]
                }
            }
    
    async def filter_relevance_batch(self, items: List[Dict]) -> List[Tuple[Dict, bool, str]]:
        """Filter items for InfoSec relevance in batches."""
        batch_size = 10
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            try:
                batch_results = await self._process_relevance_batch(batch)
                results.extend(batch_results)
                
                # Add delay to respect rate limits
                if i + batch_size < len(items):
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error processing relevance batch: {e}")
                # Add failed items with default values
                for item in batch:
                    results.append((item, False, f"API error: {str(e)}"))
        
        return results
    
    async def _process_relevance_batch(self, items: List[Dict]) -> List[Tuple[Dict, bool, str]]:
        """Process a batch of items for relevance filtering."""
        prompt = self._build_relevance_prompt(items)
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse JSON response
            response_text = response.content[0].text
            batch_results = json.loads(response_text)
            
            if not isinstance(batch_results, list) or len(batch_results) != len(items):
                raise ValueError("Invalid response format from Claude API")
            
            results = []
            for i, (item, result) in enumerate(zip(items, batch_results)):
                is_relevant = result.get("is_relevant", False)
                reasoning = result.get("reasoning", "No reasoning provided")
                results.append((item, is_relevant, reasoning))
            
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return [(item, False, "JSON parse error") for item in items]
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return [(item, False, f"API error: {str(e)}") for item in items]
    
    def _build_relevance_prompt(self, items: List[Dict]) -> str:
        """Build prompt for relevance filtering."""
        items_text = ""
        for i, item in enumerate(items, 1):
            content_excerpt = (item.get("content") or item.get("summary") or "")[:500]
            items_text += f"\nItem {i}:\nTitle: {item['title']}\nContent: {content_excerpt}\n"
        
        return f"""You are filtering RSS feed items for a Security Operations Center (SOC) analyst.

Evaluate if each item is directly relevant to information security / cybersecurity.

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

Items to evaluate:{items_text}

Respond with a JSON array containing one object per item in order:
[
  {{"is_relevant": true/false, "reasoning": "brief explanation"}},
  {{"is_relevant": true/false, "reasoning": "brief explanation"}},
  ...
]"""
    
    async def suggest_priority(self, items: List[FeedItem]) -> List[Tuple[FeedItem, bool, str, str, List[str]]]:
        """Suggest priority items based on criteria and training data."""
        results = []
        
        # Get training examples
        training_examples = await self._get_training_examples()
        
        for item in items:
            try:
                result = await self._process_priority_item(item, training_examples)
                results.append(result)
                
                # Add delay to respect rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing priority for item {item.id}: {e}")
                results.append((item, False, "low", f"API error: {str(e)}", []))
        
        return results
    
    async def _process_priority_item(self, item: FeedItem, training_examples: str) -> Tuple[FeedItem, bool, str, str, List[str]]:
        """Process a single item for priority suggestion."""
        prompt = self._build_priority_prompt(item, training_examples)
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse JSON response
            response_text = response.content[0].text
            result = json.loads(response_text)
            
            is_priority = result.get("is_priority", False)
            confidence = result.get("confidence", "low")
            reasoning = result.get("reasoning", "No reasoning provided")
            matched_criteria = result.get("matched_criteria", [])
            
            return (item, is_priority, confidence, reasoning, matched_criteria)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude priority response as JSON: {e}")
            return (item, False, "low", "JSON parse error", [])
        except Exception as e:
            logger.error(f"Claude API error for priority: {e}")
            return (item, False, "low", f"API error: {str(e)}", [])
    
    def _build_priority_prompt(self, item: FeedItem, training_examples: str) -> str:
        """Build prompt for priority suggestion."""
        criteria_yaml = yaml.dump(self.priority_criteria, default_flow_style=False)
        
        return f"""You are a SOC analyst triaging security news. Your job is to identify items that require immediate attention.

Priority criteria:
{criteria_yaml}

Training examples of items the analyst has approved/rejected:
{training_examples}

Item to evaluate:
Title: {item.title}
Content: {(item.content or item.summary or '')[:2000]}
Published: {item.published_date}
Source: {item.source_feed.name if item.source_feed else 'Unknown'}

Respond with JSON only:
{{
  "is_priority": true/false,
  "confidence": "high/medium/low",
  "reasoning": "brief explanation of why this is/isn't priority",
  "matched_criteria": ["criterion1", "criterion2"]
}}"""
    
    async def _get_training_examples(self) -> str:
        """Get training examples from database (last 10 approved/rejected items)."""
        # This would typically query the database
        # For now, return empty string as placeholder
        return "No training examples available yet."
