"""
Metrics calculation service for visibility scores and analytics.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class VisibilityMetrics:
    """Calculated visibility metrics for a brand."""
    visibility_score: float  # 0-100
    mention_rate: float  # 0-1
    sentiment_score: float  # -1 to 1
    position_score: float  # 0-100
    citation_score: float  # 0-100
    share_of_voice: float  # 0-100


@dataclass
class PlatformMetrics:
    """Metrics for a specific AI platform."""
    platform: str
    total_queries: int
    successful_queries: int
    mentions: int
    sentiment_avg: Optional[float]
    position_avg: Optional[float]
    visibility_score: float


class MetricsCalculator:
    """
    Calculator for various brand visibility metrics.

    Metrics calculated:
    - Visibility Score (0-100): Overall brand visibility
    - Share of Voice: Percentage of mentions vs competitors
    - Sentiment Score: Average sentiment (-1 to 1)
    - Position Score: Average ranking position
    - Citation Score: How often brand is cited as source
    """

    # Weights for visibility score calculation
    WEIGHTS = {
        "mention_rate": 0.30,
        "sentiment": 0.20,
        "position": 0.25,
        "citation": 0.25
    }

    def calculate_visibility_score(
        self,
        mention_rate: float,
        sentiment_score: float,
        position_score: float,
        citation_score: float
    ) -> float:
        """
        Calculate overall visibility score.

        Args:
            mention_rate: Rate of brand mentions (0-1)
            sentiment_score: Average sentiment (-1 to 1)
            position_score: Position score (0-100)
            citation_score: Citation score (0-100)

        Returns:
            Visibility score (0-100)
        """
        # Normalize sentiment to 0-100
        sentiment_normalized = (sentiment_score + 1) * 50

        # Mention rate to 0-100
        mention_normalized = mention_rate * 100

        score = (
            self.WEIGHTS["mention_rate"] * mention_normalized +
            self.WEIGHTS["sentiment"] * sentiment_normalized +
            self.WEIGHTS["position"] * position_score +
            self.WEIGHTS["citation"] * citation_score
        )

        return min(100, max(0, score))

    def calculate_mention_rate(
        self,
        total_queries: int,
        mentions: int
    ) -> float:
        """
        Calculate the rate at which brand is mentioned.

        Args:
            total_queries: Total queries executed
            mentions: Number of queries with brand mentions

        Returns:
            Mention rate (0-1)
        """
        if total_queries == 0:
            return 0.0
        return min(1.0, mentions / total_queries)

    def calculate_position_score(
        self,
        positions: List[int],
        max_position: int = 10
    ) -> float:
        """
        Calculate position score based on ranking positions.

        Higher score = better ranking (position 1 is best).

        Args:
            positions: List of ranking positions (1-indexed)
            max_position: Maximum position to consider

        Returns:
            Position score (0-100)
        """
        if not positions:
            return 0.0

        # Score = 100 * (1 - (avg_position - 1) / max_position)
        avg_position = sum(positions) / len(positions)

        # Clamp to max_position
        avg_position = min(avg_position, max_position)

        score = 100 * (1 - (avg_position - 1) / max_position)
        return max(0, score)

    def calculate_citation_score(
        self,
        brand_citations: int,
        total_citations: int
    ) -> float:
        """
        Calculate citation score based on brand source citations.

        Args:
            brand_citations: Citations from brand's domain
            total_citations: Total citations across all responses

        Returns:
            Citation score (0-100)
        """
        if total_citations == 0:
            return 0.0

        # Base score on percentage of citations from brand
        base_score = (brand_citations / total_citations) * 100

        # Bonus for absolute number of citations
        bonus = min(20, brand_citations * 2)

        return min(100, base_score + bonus)

    def calculate_share_of_voice(
        self,
        brand_mentions: int,
        competitor_mentions: Dict[str, int]
    ) -> Dict[str, float]:
        """
        Calculate share of voice for brand and competitors.

        Args:
            brand_mentions: Number of brand mentions
            competitor_mentions: Dict of competitor name -> mention count

        Returns:
            Dict with brand and competitor share of voice percentages
        """
        total_mentions = brand_mentions + sum(competitor_mentions.values())

        if total_mentions == 0:
            result = {"brand": 0.0}
            for comp in competitor_mentions:
                result[comp] = 0.0
            return result

        result = {
            "brand": (brand_mentions / total_mentions) * 100
        }

        for comp, mentions in competitor_mentions.items():
            result[comp] = (mentions / total_mentions) * 100

        return result

    def aggregate_platform_metrics(
        self,
        platform_data: Dict[str, List[Dict]]
    ) -> Dict[str, PlatformMetrics]:
        """
        Aggregate metrics for each AI platform.

        Args:
            platform_data: Dict of platform -> list of query results

        Returns:
            Dict of platform -> PlatformMetrics
        """
        results = {}

        for platform, queries in platform_data.items():
            total = len(queries)
            successful = sum(1 for q in queries if q.get("status") == "completed")
            mentions = sum(1 for q in queries if q.get("brand_mentioned"))

            sentiment_scores = [
                q.get("sentiment_score")
                for q in queries
                if q.get("sentiment_score") is not None
            ]
            sentiment_avg = (
                sum(sentiment_scores) / len(sentiment_scores)
                if sentiment_scores else None
            )

            positions = [
                q.get("position")
                for q in queries
                if q.get("position") is not None
            ]
            position_avg = (
                sum(positions) / len(positions)
                if positions else None
            )

            # Calculate platform visibility score
            mention_rate = mentions / total if total > 0 else 0
            position_score = self.calculate_position_score(positions)
            sentiment_normalized = (
                (sentiment_avg + 1) * 50 if sentiment_avg is not None else 50
            )

            visibility = (
                mention_rate * 100 * 0.4 +
                sentiment_normalized * 0.3 +
                position_score * 0.3
            )

            results[platform] = PlatformMetrics(
                platform=platform,
                total_queries=total,
                successful_queries=successful,
                mentions=mentions,
                sentiment_avg=sentiment_avg,
                position_avg=position_avg,
                visibility_score=visibility
            )

        return results

    def calculate_trend(
        self,
        current_value: float,
        previous_value: float
    ) -> Dict[str, Any]:
        """
        Calculate trend direction and change.

        Args:
            current_value: Current metric value
            previous_value: Previous metric value

        Returns:
            Dict with change amount and direction
        """
        if previous_value == 0:
            if current_value > 0:
                return {"change": current_value, "direction": "up", "percent": 100}
            return {"change": 0, "direction": "flat", "percent": 0}

        change = current_value - previous_value
        percent = (change / previous_value) * 100

        if change > 0:
            direction = "up"
        elif change < 0:
            direction = "down"
        else:
            direction = "flat"

        return {
            "change": change,
            "direction": direction,
            "percent": round(percent, 2)
        }

    def calculate_daily_metrics(
        self,
        queries: List[Dict],
        brand_name: str,
        competitors: List[str]
    ) -> VisibilityMetrics:
        """
        Calculate all metrics for a day's worth of queries.

        Args:
            queries: List of query results with analysis
            brand_name: Primary brand name
            competitors: List of competitor names

        Returns:
            VisibilityMetrics object
        """
        total_queries = len(queries)

        if total_queries == 0:
            return VisibilityMetrics(
                visibility_score=0,
                mention_rate=0,
                sentiment_score=0,
                position_score=0,
                citation_score=0,
                share_of_voice=0
            )

        # Calculate mention rate
        mentions = sum(1 for q in queries if q.get("brand_mentioned"))
        mention_rate = mentions / total_queries

        # Calculate average sentiment
        sentiment_scores = [
            q.get("sentiment_score")
            for q in queries
            if q.get("sentiment_score") is not None
        ]
        sentiment_score = (
            sum(sentiment_scores) / len(sentiment_scores)
            if sentiment_scores else 0
        )

        # Calculate position score
        positions = [
            q.get("position")
            for q in queries
            if q.get("position") is not None
        ]
        position_score = self.calculate_position_score(positions)

        # Calculate citation score
        brand_citations = sum(q.get("brand_citation_count", 0) for q in queries)
        total_citations = sum(q.get("total_citations", 0) for q in queries)
        citation_score = self.calculate_citation_score(brand_citations, total_citations)

        # Calculate share of voice
        competitor_mentions = {}
        for comp in competitors:
            comp_mentions = sum(
                q.get("competitor_mentions", {}).get(comp, {}).get("count", 0)
                for q in queries
            )
            competitor_mentions[comp] = comp_mentions

        sov_data = self.calculate_share_of_voice(mentions, competitor_mentions)

        # Calculate overall visibility score
        visibility = self.calculate_visibility_score(
            mention_rate,
            sentiment_score,
            position_score,
            citation_score
        )

        return VisibilityMetrics(
            visibility_score=visibility,
            mention_rate=mention_rate,
            sentiment_score=sentiment_score,
            position_score=position_score,
            citation_score=citation_score,
            share_of_voice=sov_data.get("brand", 0)
        )
