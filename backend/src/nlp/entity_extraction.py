"""
Entity extraction service for identifying brands, products, and features.
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import re


@dataclass
class Entity:
    """Extracted entity from text."""
    text: str
    entity_type: str  # brand, product, feature, competitor
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class BrandMention:
    """Detailed brand mention information."""
    brand: str
    count: int
    positions: List[int]
    contexts: List[str]


class EntityExtractor:
    """
    Entity extractor for brand-related entities.

    Extracts:
    - Brand mentions
    - Competitor mentions
    - Product references
    - Feature mentions
    """

    def __init__(self):
        # Common product categories (expandable)
        self.product_categories = {
            'software', 'tool', 'platform', 'app', 'application',
            'service', 'solution', 'product', 'system', 'framework'
        }

        # Common feature keywords
        self.feature_keywords = {
            'feature', 'capability', 'functionality', 'option',
            'integration', 'api', 'support', 'analytics', 'dashboard',
            'reporting', 'automation', 'security', 'pricing', 'plan'
        }

    def extract_brand_mentions(
        self,
        text: str,
        brand_name: str,
        context_window: int = 100
    ) -> BrandMention:
        """
        Extract all mentions of a brand from text.

        Args:
            text: Text to search
            brand_name: Brand name to find
            context_window: Characters before/after for context

        Returns:
            BrandMention with count, positions, and contexts
        """
        pattern = re.compile(re.escape(brand_name), re.IGNORECASE)
        positions = []
        contexts = []

        for match in pattern.finditer(text):
            positions.append(match.start())

            # Extract context
            start = max(0, match.start() - context_window)
            end = min(len(text), match.end() + context_window)
            context = text[start:end].strip()
            contexts.append(context)

        return BrandMention(
            brand=brand_name,
            count=len(positions),
            positions=positions,
            contexts=contexts
        )

    def extract_competitor_mentions(
        self,
        text: str,
        competitors: List[str],
        context_window: int = 100
    ) -> Dict[str, BrandMention]:
        """
        Extract mentions of competitors from text.

        Args:
            text: Text to search
            competitors: List of competitor names
            context_window: Characters before/after for context

        Returns:
            Dict mapping competitor name to BrandMention
        """
        results = {}

        for competitor in competitors:
            mention = self.extract_brand_mentions(text, competitor, context_window)
            if mention.count > 0:
                results[competitor] = mention

        return results

    def extract_all_entities(
        self,
        text: str,
        brand_name: str,
        competitors: Optional[List[str]] = None
    ) -> List[Entity]:
        """
        Extract all brand-related entities from text.

        Args:
            text: Text to analyze
            brand_name: Primary brand name
            competitors: Optional list of competitor names

        Returns:
            List of Entity objects
        """
        entities = []

        # Extract primary brand
        pattern = re.compile(re.escape(brand_name), re.IGNORECASE)
        for match in pattern.finditer(text):
            entities.append(Entity(
                text=match.group(),
                entity_type="brand",
                start=match.start(),
                end=match.end()
            ))

        # Extract competitors
        if competitors:
            for competitor in competitors:
                pattern = re.compile(re.escape(competitor), re.IGNORECASE)
                for match in pattern.finditer(text):
                    entities.append(Entity(
                        text=match.group(),
                        entity_type="competitor",
                        start=match.start(),
                        end=match.end()
                    ))

        return entities

    def find_brand_in_list(
        self,
        text: str,
        brand_name: str
    ) -> Optional[int]:
        """
        Find the position of a brand in a numbered list.

        Args:
            text: Text containing numbered list
            brand_name: Brand to find

        Returns:
            1-based position or None if not in list
        """
        # Pattern for numbered list items
        list_pattern = r'^\s*(\d+)[.)]\s*(.+)$'

        lines = text.split('\n')
        for line in lines:
            match = re.match(list_pattern, line, re.MULTILINE)
            if match:
                position = int(match.group(1))
                item_text = match.group(2)

                if re.search(re.escape(brand_name), item_text, re.IGNORECASE):
                    return position

        return None

    def count_total_recommendations(self, text: str) -> int:
        """
        Count total items in a recommendation list.

        Args:
            text: Text containing list

        Returns:
            Number of items in list
        """
        # Pattern for numbered list items
        list_pattern = r'^\s*\d+[.)]\s*.+$'

        lines = text.split('\n')
        count = 0

        for line in lines:
            if re.match(list_pattern, line, re.MULTILINE):
                count += 1

        return count

    def extract_comparison_entities(
        self,
        text: str,
        brand_name: str,
        competitors: List[str]
    ) -> Dict[str, Dict]:
        """
        Extract comparison data when brand is compared to competitors.

        Args:
            text: Text with comparisons
            brand_name: Primary brand
            competitors: Competitor names

        Returns:
            Dict with comparison data
        """
        results = {
            "brand": {"name": brand_name, "mentioned": False, "favorable": None},
            "competitors": {}
        }

        # Check if brand is mentioned
        if re.search(re.escape(brand_name), text, re.IGNORECASE):
            results["brand"]["mentioned"] = True

        # Check competitors
        for comp in competitors:
            comp_data = {"mentioned": False, "favorable": None}
            if re.search(re.escape(comp), text, re.IGNORECASE):
                comp_data["mentioned"] = True
            results["competitors"][comp] = comp_data

        # Try to detect favorable language
        favorable_patterns = [
            r'(\w+)\s+is\s+(?:better|best|superior|preferred)',
            r'recommend\s+(\w+)',
            r'(\w+)\s+(?:wins|leads|excels)',
        ]

        for pattern in favorable_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if re.search(re.escape(brand_name), match, re.IGNORECASE):
                    results["brand"]["favorable"] = True
                for comp in competitors:
                    if re.search(re.escape(comp), match, re.IGNORECASE):
                        results["competitors"][comp]["favorable"] = True

        return results
