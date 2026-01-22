"""
Sentiment analysis service for brand mentions.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import re


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    label: str  # positive, negative, neutral
    score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    context: Optional[str] = None


@dataclass
class AspectSentiment:
    """Sentiment for a specific aspect (pricing, features, support, etc.)."""
    aspect: str
    label: str  # positive, negative, neutral
    score: float  # -1.0 to 1.0
    evidence: List[str] = field(default_factory=list)  # Text snippets showing this sentiment
    mention_count: int = 0


@dataclass
class DetailedSentimentResult:
    """Comprehensive sentiment analysis with aspect breakdown."""
    overall: SentimentResult
    aspects: List[AspectSentiment]
    dominant_aspect: Optional[str] = None
    aspect_summary: Dict[str, float] = field(default_factory=dict)  # aspect -> score


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

        # Aspect-specific keywords for aspect-based sentiment analysis
        self.aspect_keywords = {
            'pricing': {
                'keywords': ['price', 'pricing', 'cost', 'expensive', 'cheap', 'affordable',
                            'free', 'premium', 'plan', 'subscription', 'value', 'worth', 'budget'],
                'positive': ['affordable', 'free', 'value', 'worth', 'reasonable', 'fair', 'budget-friendly'],
                'negative': ['expensive', 'overpriced', 'costly', 'pricey', 'not worth']
            },
            'features': {
                'keywords': ['feature', 'capability', 'functionality', 'option', 'tool',
                            'function', 'ability', 'power', 'advanced'],
                'positive': ['powerful', 'advanced', 'comprehensive', 'rich', 'extensive', 'robust'],
                'negative': ['limited', 'lacking', 'basic', 'missing', 'incomplete']
            },
            'support': {
                'keywords': ['support', 'help', 'service', 'customer', 'response', 'team',
                            'documentation', 'docs', 'community'],
                'positive': ['responsive', 'helpful', 'quick', 'excellent', 'friendly', 'knowledgeable'],
                'negative': ['slow', 'unhelpful', 'unresponsive', 'poor', 'terrible', 'lacking']
            },
            'ease_of_use': {
                'keywords': ['easy', 'simple', 'intuitive', 'user-friendly', 'complex', 'difficult',
                            'learning curve', 'setup', 'onboarding', 'ui', 'interface', 'ux'],
                'positive': ['easy', 'simple', 'intuitive', 'user-friendly', 'straightforward', 'clean'],
                'negative': ['complex', 'difficult', 'confusing', 'complicated', 'steep learning curve', 'clunky']
            },
            'performance': {
                'keywords': ['fast', 'slow', 'performance', 'speed', 'reliable', 'stable',
                            'crash', 'bug', 'uptime', 'downtime', 'lag'],
                'positive': ['fast', 'quick', 'reliable', 'stable', 'smooth', 'responsive'],
                'negative': ['slow', 'buggy', 'crashes', 'unreliable', 'unstable', 'laggy', 'downtime']
            },
            'integration': {
                'keywords': ['integration', 'integrate', 'connect', 'api', 'plugin', 'extension',
                            'compatibility', 'sync', 'import', 'export'],
                'positive': ['seamless', 'easy integration', 'compatible', 'connects well'],
                'negative': ['incompatible', 'difficult to integrate', 'limited integrations']
            },
            'security': {
                'keywords': ['security', 'secure', 'privacy', 'safe', 'encryption', 'compliance',
                            'gdpr', 'soc2', 'data protection'],
                'positive': ['secure', 'safe', 'encrypted', 'compliant', 'protected'],
                'negative': ['insecure', 'vulnerable', 'breach', 'exposed', 'risk']
            }
        }

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

    def analyze_with_aspects(
        self,
        text: str,
        brand: str,
        context_window: int = 150
    ) -> DetailedSentimentResult:
        """
        Analyze sentiment with aspect-level breakdown.

        For each aspect (pricing, features, support, etc.):
        1. Find sentences mentioning both brand AND aspect keywords
        2. Analyze sentiment of those sentences
        3. Return aspect-level breakdown

        Args:
            text: Full text to analyze
            brand: Brand name
            context_window: Characters around brand mention

        Returns:
            DetailedSentimentResult with overall and aspect breakdown
        """
        # Get overall sentiment
        overall = self.analyze_mention(text, brand, context_window)

        # Split text into sentences for aspect analysis
        sentences = re.split(r'[.!?]+', text)

        # Analyze each aspect
        aspect_results = []
        aspect_scores = {}

        for aspect_name, aspect_data in self.aspect_keywords.items():
            aspect_sentences = []
            evidence = []

            # Find sentences containing brand AND aspect keywords
            for sentence in sentences:
                sentence_lower = sentence.lower()
                brand_in_sentence = brand.lower() in sentence_lower

                # Check if any aspect keyword is in sentence
                has_aspect_keyword = any(
                    kw in sentence_lower for kw in aspect_data['keywords']
                )

                if has_aspect_keyword:
                    # Either brand is in sentence, or it's near brand mentions
                    aspect_sentences.append(sentence.strip())
                    if brand_in_sentence:
                        evidence.append(sentence.strip()[:200])

            if not aspect_sentences:
                continue

            # Calculate sentiment for this aspect
            positive_count = 0
            negative_count = 0

            for sentence in aspect_sentences:
                sentence_lower = sentence.lower()

                # Check aspect-specific positive words
                for pos_word in aspect_data['positive']:
                    if pos_word in sentence_lower:
                        positive_count += 1

                # Check aspect-specific negative words
                for neg_word in aspect_data['negative']:
                    if neg_word in sentence_lower:
                        negative_count += 1

                # Also check general sentiment words
                for word in self.positive_words:
                    if word in sentence_lower:
                        positive_count += 0.5

                for word in self.negative_words:
                    if word in sentence_lower:
                        negative_count += 0.5

            # Calculate aspect score
            total = positive_count + negative_count
            if total > 0:
                aspect_score = (positive_count - negative_count) / total
            else:
                aspect_score = 0.0

            # Determine label
            if aspect_score > 0.2:
                aspect_label = "positive"
            elif aspect_score < -0.2:
                aspect_label = "negative"
            else:
                aspect_label = "neutral"

            aspect_results.append(AspectSentiment(
                aspect=aspect_name,
                label=aspect_label,
                score=round(aspect_score, 3),
                evidence=evidence[:3],  # Top 3 evidence snippets
                mention_count=len(aspect_sentences)
            ))

            aspect_scores[aspect_name] = aspect_score

        # Determine dominant aspect (most mentioned or strongest sentiment)
        dominant_aspect = None
        if aspect_results:
            # Sort by mention count, then by absolute sentiment score
            sorted_aspects = sorted(
                aspect_results,
                key=lambda x: (x.mention_count, abs(x.score)),
                reverse=True
            )
            if sorted_aspects:
                dominant_aspect = sorted_aspects[0].aspect

        return DetailedSentimentResult(
            overall=overall,
            aspects=aspect_results,
            dominant_aspect=dominant_aspect,
            aspect_summary=aspect_scores
        )

    def get_aspect_summary_for_brand(
        self,
        texts: List[str],
        brand: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate aspect sentiment across multiple texts.

        Args:
            texts: List of texts to analyze
            brand: Brand name

        Returns:
            Dict with aspect -> {avg_score, total_mentions, sentiment_label}
        """
        aspect_data = {aspect: {'scores': [], 'mentions': 0}
                      for aspect in self.aspect_keywords.keys()}

        for text in texts:
            result = self.analyze_with_aspects(text, brand)

            for aspect in result.aspects:
                aspect_data[aspect.aspect]['scores'].append(aspect.score)
                aspect_data[aspect.aspect]['mentions'] += aspect.mention_count

        # Calculate aggregates
        summary = {}
        for aspect, data in aspect_data.items():
            if data['scores']:
                avg_score = sum(data['scores']) / len(data['scores'])
            else:
                avg_score = 0.0

            if avg_score > 0.2:
                label = "positive"
            elif avg_score < -0.2:
                label = "negative"
            else:
                label = "neutral"

            summary[aspect] = {
                'avg_score': round(avg_score, 3),
                'total_mentions': data['mentions'],
                'sentiment_label': label,
                'sample_count': len(data['scores'])
            }

        return summary
