"""
Entity extraction service for identifying brands, products, and features.
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import re


class MentionType(str, Enum):
    """Type of brand mention based on context."""
    RECOMMENDATION = "recommendation"
    CRITICISM = "criticism"
    COMPARISON = "comparison"
    NEUTRAL = "neutral"
    FEATURE_HIGHLIGHT = "feature_highlight"


@dataclass
class ContextualMention:
    """Brand mention with context classification."""
    brand: str
    context: str
    mention_type: MentionType
    position_in_text: int
    comparison_target: Optional[str] = None  # Competitor being compared to
    comparison_winner: Optional[str] = None  # Who "wins" the comparison
    aspects_mentioned: List[str] = field(default_factory=list)  # pricing, features, support, etc.
    confidence: float = 0.5


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

    def extract_contextual_mentions(
        self,
        text: str,
        brand_name: str,
        competitors: Optional[List[str]] = None
    ) -> List[ContextualMention]:
        """
        Extract mentions with context classification (recommendation, criticism, comparison, etc.).

        Args:
            text: Text to analyze
            brand_name: Primary brand name
            competitors: Optional list of competitor names

        Returns:
            List of ContextualMention objects with type classification
        """
        mentions = []
        competitors = competitors or []

        # Recommendation patterns
        recommendation_patterns = [
            r'(?:recommend|suggesting?|try|choose|go\s+with|opt\s+for|pick)\s+' + re.escape(brand_name),
            re.escape(brand_name) + r'\s+(?:is\s+)?(?:the\s+)?(?:best|top|leading|excellent|great|ideal|perfect|recommended)',
            r'(?:best\s+choice|top\s+pick|first\s+choice|go-to|standout)(?:[^.]*?)' + re.escape(brand_name),
            r'(?:highly\s+recommend|strongly\s+suggest)(?:[^.]*?)' + re.escape(brand_name),
        ]

        # Criticism patterns
        criticism_patterns = [
            r'(?:avoid|don\'t\s+use|stay\s+away\s+from|skip)\s+' + re.escape(brand_name),
            re.escape(brand_name) + r'\s+(?:is\s+)?(?:poor|bad|terrible|disappointing|lacking|limited|expensive|overpriced)',
            r'(?:problems?\s+with|issues?\s+with|downsides?\s+of|drawbacks?\s+of)(?:[^.]*?)' + re.escape(brand_name),
            re.escape(brand_name) + r'(?:[^.]*?)(?:falls\s+short|doesn\'t\s+deliver|fails\s+to)',
        ]

        # Comparison patterns
        comparison_patterns = [
            re.escape(brand_name) + r'\s+(?:vs\.?|versus|compared\s+to|or)\s+(\w+)',
            r'(\w+)\s+(?:vs\.?|versus|compared\s+to|or)\s+' + re.escape(brand_name),
            re.escape(brand_name) + r'\s+(?:is\s+)?(?:better|worse|faster|slower|cheaper|more\s+expensive)\s+than\s+(\w+)',
            r'(\w+)\s+(?:is\s+)?(?:better|worse|faster|slower|cheaper|more\s+expensive)\s+than\s+' + re.escape(brand_name),
        ]

        # Feature highlight patterns
        feature_patterns = [
            re.escape(brand_name) + r'(?:[^.]*?)(?:offers?|provides?|includes?|features?|has)\s+(\w+(?:\s+\w+)?)',
            re.escape(brand_name) + r'\'s\s+(\w+(?:\s+\w+)?)\s+(?:feature|capability|functionality)',
        ]

        # Aspect keywords
        aspect_keywords = {
            'pricing': ['price', 'pricing', 'cost', 'expensive', 'cheap', 'affordable', 'free', 'premium', 'plan', 'subscription'],
            'features': ['feature', 'capability', 'functionality', 'option', 'tool', 'function'],
            'support': ['support', 'help', 'service', 'customer', 'response', 'team'],
            'ease_of_use': ['easy', 'simple', 'intuitive', 'user-friendly', 'complex', 'difficult', 'learning curve'],
            'performance': ['fast', 'slow', 'performance', 'speed', 'reliable', 'stable', 'crash'],
            'integration': ['integration', 'integrate', 'connect', 'api', 'plugin', 'extension'],
            'security': ['security', 'secure', 'privacy', 'safe', 'encryption', 'compliance'],
        }

        # Find brand in text
        brand_pattern = re.compile(re.escape(brand_name), re.IGNORECASE)

        for match in brand_pattern.finditer(text):
            position = match.start()

            # Get context (200 chars before and after)
            start = max(0, position - 200)
            end = min(len(text), match.end() + 200)
            context = text[start:end].strip()

            # Classify mention type
            mention_type = MentionType.NEUTRAL
            confidence = 0.5
            comparison_target = None
            comparison_winner = None

            # Check recommendation patterns
            for pattern in recommendation_patterns:
                if re.search(pattern, context, re.IGNORECASE):
                    mention_type = MentionType.RECOMMENDATION
                    confidence = 0.8
                    break

            # Check criticism patterns (if not already classified)
            if mention_type == MentionType.NEUTRAL:
                for pattern in criticism_patterns:
                    if re.search(pattern, context, re.IGNORECASE):
                        mention_type = MentionType.CRITICISM
                        confidence = 0.8
                        break

            # Check comparison patterns (can override neutral)
            if mention_type == MentionType.NEUTRAL:
                for pattern in comparison_patterns:
                    comp_match = re.search(pattern, context, re.IGNORECASE)
                    if comp_match:
                        mention_type = MentionType.COMPARISON
                        confidence = 0.75
                        # Extract comparison target
                        if comp_match.groups():
                            potential_target = comp_match.group(1)
                            # Verify it's a known competitor
                            for comp in competitors:
                                if comp.lower() in potential_target.lower():
                                    comparison_target = comp
                                    break
                            if not comparison_target:
                                comparison_target = potential_target
                        break

            # Check feature patterns (can override neutral)
            if mention_type == MentionType.NEUTRAL:
                for pattern in feature_patterns:
                    if re.search(pattern, context, re.IGNORECASE):
                        mention_type = MentionType.FEATURE_HIGHLIGHT
                        confidence = 0.7
                        break

            # Determine comparison winner if it's a comparison
            if mention_type == MentionType.COMPARISON and comparison_target:
                winner_patterns = [
                    (re.escape(brand_name) + r'\s+(?:is\s+)?(?:better|superior|preferred|wins)', brand_name),
                    (re.escape(comparison_target) + r'\s+(?:is\s+)?(?:better|superior|preferred|wins)', comparison_target),
                    (r'(?:choose|recommend|prefer)\s+' + re.escape(brand_name), brand_name),
                    (r'(?:choose|recommend|prefer)\s+' + re.escape(comparison_target), comparison_target),
                ]
                for pattern, winner in winner_patterns:
                    if re.search(pattern, context, re.IGNORECASE):
                        comparison_winner = winner
                        break

            # Extract aspects mentioned
            aspects_found = []
            context_lower = context.lower()
            for aspect, keywords in aspect_keywords.items():
                for keyword in keywords:
                    if keyword in context_lower:
                        aspects_found.append(aspect)
                        break

            mentions.append(ContextualMention(
                brand=brand_name,
                context=context,
                mention_type=mention_type,
                position_in_text=position,
                comparison_target=comparison_target,
                comparison_winner=comparison_winner,
                aspects_mentioned=aspects_found,
                confidence=confidence
            ))

        return mentions

    def get_mention_type_summary(
        self,
        mentions: List[ContextualMention]
    ) -> Dict[str, any]:
        """
        Summarize mention types for analytics.

        Args:
            mentions: List of contextual mentions

        Returns:
            Dict with type counts and comparison stats
        """
        summary = {
            "total": len(mentions),
            "by_type": {
                "recommendation": 0,
                "criticism": 0,
                "comparison": 0,
                "neutral": 0,
                "feature_highlight": 0
            },
            "comparison_stats": {
                "total_comparisons": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "targets": {}
            },
            "aspects": {}
        }

        for mention in mentions:
            # Count by type
            summary["by_type"][mention.mention_type.value] += 1

            # Track comparisons
            if mention.mention_type == MentionType.COMPARISON:
                summary["comparison_stats"]["total_comparisons"] += 1
                if mention.comparison_winner:
                    if mention.comparison_winner == mention.brand:
                        summary["comparison_stats"]["wins"] += 1
                    else:
                        summary["comparison_stats"]["losses"] += 1
                else:
                    summary["comparison_stats"]["draws"] += 1

                if mention.comparison_target:
                    target = mention.comparison_target
                    if target not in summary["comparison_stats"]["targets"]:
                        summary["comparison_stats"]["targets"][target] = 0
                    summary["comparison_stats"]["targets"][target] += 1

            # Count aspects
            for aspect in mention.aspects_mentioned:
                if aspect not in summary["aspects"]:
                    summary["aspects"][aspect] = 0
                summary["aspects"][aspect] += 1

        return summary
