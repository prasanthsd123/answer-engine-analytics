"""
Sentiment analysis service for brand mentions.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import re


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    label: str  # positive, negative, neutral
    score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    context: Optional[str] = None


class SentimentAnalyzer:
    """
    Sentiment analyzer for brand mentions.

    Uses a combination of rule-based and ML approaches.
    For production, this would use transformers models like
    cardiffnlp/twitter-roberta-base-sentiment-latest
    """

    def __init__(self, use_ml_model: bool = False):
        self.use_ml_model = use_ml_model
        self._model = None
        self._tokenizer = None

        # Sentiment lexicons (simplified)
        self.positive_words = {
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'best', 'love', 'loved', 'recommend', 'recommended', 'reliable',
            'easy', 'fast', 'efficient', 'professional', 'quality', 'impressive',
            'outstanding', 'superb', 'perfect', 'brilliant', 'top', 'leading',
            'innovative', 'powerful', 'useful', 'helpful', 'effective', 'affordable'
        }

        self.negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'poor', 'worst',
            'hate', 'disappointing', 'disappointed', 'unreliable', 'expensive',
            'slow', 'difficult', 'complicated', 'frustrating', 'annoying',
            'confusing', 'buggy', 'broken', 'useless', 'overpriced', 'lacking',
            'mediocre', 'subpar', 'avoid', 'scam', 'waste', 'problems', 'issues'
        }

        self.negation_words = {'not', 'no', 'never', "n't", 'neither', 'nobody', 'nothing'}

        if use_ml_model:
            self._load_model()

    def _load_model(self):
        """Load the ML model for sentiment analysis."""
        try:
            from transformers import pipeline
            self._model = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
        except Exception as e:
            print(f"Failed to load ML model: {e}")
            self.use_ml_model = False

    def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            SentimentResult with label, score, and confidence
        """
        if self.use_ml_model and self._model:
            return self._analyze_ml(text)
        return self._analyze_rule_based(text)

    def _analyze_ml(self, text: str) -> SentimentResult:
        """Analyze sentiment using ML model."""
        try:
            # Truncate text to model's max length
            text = text[:512]
            result = self._model(text)[0]

            # Map model labels to our format
            label_map = {
                'positive': ('positive', 1.0),
                'negative': ('negative', -1.0),
                'neutral': ('neutral', 0.0),
                'POSITIVE': ('positive', 1.0),
                'NEGATIVE': ('negative', -1.0),
                'NEUTRAL': ('neutral', 0.0),
            }

            label, base_score = label_map.get(result['label'], ('neutral', 0.0))
            confidence = result['score']
            score = base_score * confidence

            return SentimentResult(
                label=label,
                score=score,
                confidence=confidence
            )
        except Exception:
            return self._analyze_rule_based(text)

    def _analyze_rule_based(self, text: str) -> SentimentResult:
        """Analyze sentiment using rule-based approach."""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        positive_count = 0
        negative_count = 0

        # Check for negation
        for i, word in enumerate(words):
            is_negated = False
            # Check previous 3 words for negation
            for j in range(max(0, i - 3), i):
                if words[j] in self.negation_words:
                    is_negated = True
                    break

            if word in self.positive_words:
                if is_negated:
                    negative_count += 1
                else:
                    positive_count += 1
            elif word in self.negative_words:
                if is_negated:
                    positive_count += 1
                else:
                    negative_count += 1

        total = positive_count + negative_count
        if total == 0:
            return SentimentResult(
                label="neutral",
                score=0.0,
                confidence=0.5
            )

        # Calculate score
        score = (positive_count - negative_count) / total
        confidence = min(0.9, total / 10)  # More words = more confidence, max 0.9

        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        else:
            label = "neutral"

        return SentimentResult(
            label=label,
            score=score,
            confidence=confidence
        )

    def analyze_mention(self, text: str, brand: str, context_window: int = 100) -> SentimentResult:
        """
        Analyze sentiment around a brand mention.

        Args:
            text: Full text
            brand: Brand name to find
            context_window: Characters before/after mention to analyze

        Returns:
            SentimentResult for the mention context
        """
        pattern = re.compile(re.escape(brand), re.IGNORECASE)
        match = pattern.search(text)

        if not match:
            return SentimentResult(
                label="neutral",
                score=0.0,
                confidence=0.0
            )

        # Extract context around mention
        start = max(0, match.start() - context_window)
        end = min(len(text), match.end() + context_window)
        context = text[start:end]

        result = self.analyze(context)
        result.context = context

        return result

    def analyze_multiple_mentions(
        self,
        text: str,
        brand: str
    ) -> List[SentimentResult]:
        """
        Analyze sentiment for all mentions of a brand.

        Args:
            text: Full text
            brand: Brand name to find

        Returns:
            List of SentimentResult for each mention
        """
        results = []
        pattern = re.compile(re.escape(brand), re.IGNORECASE)

        for match in pattern.finditer(text):
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]

            result = self.analyze(context)
            result.context = context
            results.append(result)

        return results

    def aggregate_sentiment(self, results: List[SentimentResult]) -> SentimentResult:
        """
        Aggregate multiple sentiment results into one.

        Args:
            results: List of sentiment results

        Returns:
            Aggregated SentimentResult
        """
        if not results:
            return SentimentResult(
                label="neutral",
                score=0.0,
                confidence=0.0
            )

        # Weighted average by confidence
        total_weight = sum(r.confidence for r in results)
        if total_weight == 0:
            return SentimentResult(
                label="neutral",
                score=0.0,
                confidence=0.0
            )

        weighted_score = sum(r.score * r.confidence for r in results) / total_weight
        avg_confidence = total_weight / len(results)

        if weighted_score > 0.2:
            label = "positive"
        elif weighted_score < -0.2:
            label = "negative"
        else:
            label = "neutral"

        return SentimentResult(
            label=label,
            score=weighted_score,
            confidence=avg_confidence
        )
