"""
Router Agent for Smart Model Router.

This module classifies prompts and determines which model tier to use.
It's designed with an abstract interface so we can swap implementations:
- RuleBasedRouter: Current implementation using heuristics
- LLMRouter: Future implementation using lightweight LLM for classification
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.config import get_settings


class DifficultyTier(str, Enum):
    """Difficulty tiers that map to different models."""
    SIMPLE = "simple"    # Cheapest tier  (gemini-2.0-flash-lite)
    MEDIUM = "medium"    # Mid tier       (gemini-2.0-flash)
    COMPLEX = "complex"  # Strongest tier (gemini-2.5-pro)


@dataclass
class RoutingDecision:
    """
    Result of the routing decision.
    
    Attributes:
        tier: The difficulty tier (simple/medium/complex)
        model: The specific model to use
        reason: Human-readable explanation of why this tier was chosen
        confidence: How confident the router is (0.0 to 1.0)
    """
    tier: DifficultyTier
    model: str
    reason: str
    confidence: float = 1.0


@dataclass
class PromptAnalysis:
    """
    Analysis of a prompt's characteristics.
    
    Used by the router to make decisions.
    """
    token_count: int
    word_count: int
    has_code_block: bool
    has_code_keywords: bool
    has_reasoning_keywords: bool
    has_simple_keywords: bool
    question_count: int
    instruction_complexity: int  # 1-5 scale


# Phrases that force COMPLEX regardless of which router mode is active.
# Originally lived only inside RuleBasedRouter.classify, so it silently did
# nothing whenever use_llm_router=True (the default) -- a user explicitly
# asking for "the best model" got whatever the LLM classifier guessed instead.
BEST_MODEL_TRIGGERS = ("best model", "highest quality", "most accurate", "gpt-4", "most capable")


def _best_model_override(prompt: str) -> bool:
    """Whether the prompt explicitly asks for the top-tier model."""
    text_lower = prompt.lower()
    return any(trigger in text_lower for trigger in BEST_MODEL_TRIGGERS)


class BaseRouter(ABC):
    """
    Abstract base class for routers.
    
    Allows swapping between rule-based and LLM-based routing.
    """
    
    @abstractmethod
    async def classify(self, prompt: str, force_tier: Optional[str] = None) -> RoutingDecision:
        """
        Classify a prompt and return routing decision.
        
        Args:
            prompt: The user's prompt text
            force_tier: Optional override to force a specific tier
            
        Returns:
            RoutingDecision with tier, model, and reasoning
        """
        pass
    
    @abstractmethod
    def analyze_prompt(self, prompt: str) -> PromptAnalysis:
        """
        Analyze prompt characteristics.
        
        Args:
            prompt: The user's prompt text
            
        Returns:
            PromptAnalysis with extracted features
        """
        pass


class RuleBasedRouter(BaseRouter):
    """
    Rule-based router using heuristics.
    
    Classifies prompts based on:
    - Token/word count
    - Presence of code
    - Keywords indicating complexity
    - Question structure
    """
    
    # Keywords indicating simple tasks
    SIMPLE_KEYWORDS = {
        "summarize", "summary", "summarise", "tldr", "tl;dr",
        "translate", "translation",
        "rewrite", "rephrase", "paraphrase",
        "extract", "list", "bullet points",
        "define", "definition", "what is", "what are",
        "format", "convert", "fix grammar", "proofread",
        "yes or no", "true or false",
    }
    
    # Keywords indicating medium complexity
    MEDIUM_KEYWORDS = {
        "explain", "describe", "compare", "contrast",
        "analyze", "analyse", "evaluate",
        "write a", "create a", "generate",
        "how to", "how do", "how does", "how can",
        "why", "what if",
        "example", "examples",
        "code", "function", "script", "program",
        "json", "xml", "yaml", "csv",
    }
    
    # Keywords indicating complex tasks
    COMPLEX_KEYWORDS = {
        "architect", "architecture", "design system",
        "debug", "fix this", "why isn't", "why doesn't",
        "optimize", "optimise", "performance",
        "refactor", "restructure", "redesign",
        "multiple steps", "step by step", "step-by-step",
        "pros and cons", "trade-offs", "tradeoffs",
        "implement", "build", "develop",
        "algorithm", "data structure",
        "best model", "highest quality", "most accurate",
        "complex", "advanced", "sophisticated",
        "security", "authentication", "authorization",
        "database schema", "api design", "system design",
    }
    
    # Code-related patterns
    CODE_PATTERNS = {
        "```", "def ", "function ", "class ",
        "import ", "from ", "const ", "let ", "var ",
        "public ", "private ", "async ", "await ",
        "SELECT ", "INSERT ", "UPDATE ", "DELETE ",
        "CREATE TABLE", "ALTER TABLE",
    }
    
    def __init__(self):
        """Initialize with settings."""
        self.settings = get_settings()
        
        # Model mapping
        self.model_map = {
            DifficultyTier.SIMPLE: self.settings.tier_simple_model,
            DifficultyTier.MEDIUM: self.settings.tier_medium_model,
            DifficultyTier.COMPLEX: self.settings.tier_complex_model,
        }
    
    def _count_tokens(self, text: str) -> int:
        """
        Approximate token count.
        
        Simple heuristic: ~4 characters per token for English.
        For accurate counts, we'd use tiktoken, but this is faster.
        """
        return len(text) // 4
    
    def _has_keywords(self, text_lower: str, keywords: set) -> bool:
        """Check if text contains any of the keywords."""
        return any(kw in text_lower for kw in keywords)
    
    def _count_questions(self, text: str) -> int:
        """Count the number of questions in the text."""
        return text.count("?")
    
    def _has_code_block(self, text: str) -> bool:
        """Check if text contains code blocks."""
        return "```" in text or text.count("    ") > 3  # Indented code
    
    def _has_code_patterns(self, text: str) -> bool:
        """Check for code-like patterns."""
        return any(pattern in text for pattern in self.CODE_PATTERNS)
    
    def _estimate_instruction_complexity(self, text: str) -> int:
        """
        Estimate instruction complexity on a 1-5 scale.
        
        Based on:
        - Number of distinct requests/tasks
        - Presence of conditional logic (if, when, unless)
        - Multi-step requirements
        """
        text_lower = text.lower()
        score = 1
        
        # Multiple requests?
        if text.count(". ") > 3 or text.count("\n") > 5:
            score += 1
        
        # Conditional logic?
        conditionals = ["if ", "when ", "unless ", "only if", "except"]
        if any(c in text_lower for c in conditionals):
            score += 1
        
        # Multi-step?
        step_indicators = ["first", "then", "next", "finally", "step 1", "1.", "2.", "3."]
        if sum(1 for s in step_indicators if s in text_lower) >= 2:
            score += 1
        
        # Very long prompt?
        if len(text) > 2000:
            score += 1
        
        return min(score, 5)
    
    def analyze_prompt(self, prompt: str) -> PromptAnalysis:
        """Analyze the prompt and extract features."""
        text_lower = prompt.lower()
        
        return PromptAnalysis(
            token_count=self._count_tokens(prompt),
            word_count=len(prompt.split()),
            has_code_block=self._has_code_block(prompt),
            has_code_keywords=self._has_code_patterns(prompt),
            has_reasoning_keywords=self._has_keywords(text_lower, self.COMPLEX_KEYWORDS),
            has_simple_keywords=self._has_keywords(text_lower, self.SIMPLE_KEYWORDS),
            question_count=self._count_questions(prompt),
            instruction_complexity=self._estimate_instruction_complexity(prompt),
        )
    
    async def classify(self, prompt: str, force_tier: Optional[str] = None) -> RoutingDecision:
        """
        Classify the prompt using rule-based heuristics.
        
        Decision flow:
        1. Check for forced tier override
        2. Check for "best model" override keywords
        3. Analyze prompt features
        4. Apply scoring rules
        5. Return decision with explanation
        """
        settings = self.settings
        
        # 1. Handle forced tier
        if force_tier:
            tier = DifficultyTier(force_tier)
            return RoutingDecision(
                tier=tier,
                model=self.model_map[tier],
                reason=f"Forced to {force_tier} tier by request",
                confidence=1.0,
            )
        
        # 2. Check for "best model" override
        if _best_model_override(prompt):
            return RoutingDecision(
                tier=DifficultyTier.COMPLEX,
                model=self.model_map[DifficultyTier.COMPLEX],
                reason="User requested best/highest quality model",
                confidence=0.95,
            )

        # 3. Analyze prompt
        analysis = self.analyze_prompt(prompt)
        
        # 4. Scoring logic
        score = 0  # Start neutral, negative = simple, positive = complex
        reasons = []
        
        # Token count thresholds
        if analysis.token_count < settings.simple_token_threshold:
            score -= 2
            reasons.append(f"Short prompt ({analysis.token_count} tokens)")
        elif analysis.token_count > settings.complex_token_threshold:
            score += 2
            reasons.append(f"Long prompt ({analysis.token_count} tokens)")
        
        # Code detection
        if analysis.has_code_block:
            score += 2
            reasons.append("Contains code blocks")
        elif analysis.has_code_keywords:
            score += 1
            reasons.append("Contains code patterns")
        
        # Keyword detection
        if analysis.has_simple_keywords and not analysis.has_reasoning_keywords:
            score -= 2
            reasons.append("Simple task keywords detected")
        
        if analysis.has_reasoning_keywords:
            score += 2
            reasons.append("Complex reasoning keywords detected")
        
        # Instruction complexity
        if analysis.instruction_complexity >= 4:
            score += 2
            reasons.append(f"High instruction complexity ({analysis.instruction_complexity}/5)")
        elif analysis.instruction_complexity <= 2:
            score -= 1
            reasons.append(f"Low instruction complexity ({analysis.instruction_complexity}/5)")
        
        # Multiple questions = more complex
        if analysis.question_count > 3:
            score += 1
            reasons.append(f"Multiple questions ({analysis.question_count})")
        
        # 5. Map score to tier
        if score <= -2:
            tier = DifficultyTier.SIMPLE
        elif score >= 3:
            tier = DifficultyTier.COMPLEX
        else:
            tier = DifficultyTier.MEDIUM
        
        # Calculate confidence based on how decisive the score is
        confidence = min(0.9, 0.5 + abs(score) * 0.1)
        
        return RoutingDecision(
            tier=tier,
            model=self.model_map[tier],
            reason="; ".join(reasons) if reasons else "Default classification",
            confidence=confidence,
        )


# Default router instance
_router: Optional[BaseRouter] = None
_rule_router: Optional[RuleBasedRouter] = None


class LLMRouter(BaseRouter):
    """
    LLM-based router that asks a cheap model to grade prompt complexity.

    Classification runs on every request, so the classifier must be far cheaper
    than the tier spread it is choosing between -- otherwise the classification
    call costs more than the routing saves. It uses the cheapest tier model
    (settings.classifier_model) and caps output at a handful of tokens.

    Falls back to RuleBasedRouter if the LLM call fails for any reason.
    """
    
    # Classification prompt template
    CLASSIFICATION_PROMPT = """You are a prompt classifier. Analyze the following user prompt and classify its complexity.

User Prompt:
{prompt}

Classify this prompt into ONE of these categories:
- SIMPLE: Basic tasks like summarization, translation, simple Q&A, formatting
- MEDIUM: Explanations, code generation, comparisons, moderate analysis
- COMPLEX: Architecture design, debugging, multi-step reasoning, advanced analysis

Respond with ONLY the category name (SIMPLE, MEDIUM, or COMPLEX) and a brief reason.
Format: CATEGORY|reason

Example: SIMPLE|This is a basic translation request"""

    def __init__(self):
        """Initialize with fallback router."""
        self.settings = get_settings()
        self._fallback_router = RuleBasedRouter()
        self._provider = None
        self.last_used_fallback = False  # Set per-call; read by the eval harness
        self.last_response = None  # ProviderResponse from the most recent LLM call, if any -- lets callers (e.g. the eval harness) cost out classification itself
        self.last_error = None  # Exception from the most recent failed LLM call, if any -- lets callers distinguish e.g. rate limits (worth a long backoff) from other failures

        # Model mapping
        self.model_map = {
            DifficultyTier.SIMPLE: self.settings.tier_simple_model,
            DifficultyTier.MEDIUM: self.settings.tier_medium_model,
            DifficultyTier.COMPLEX: self.settings.tier_complex_model,
        }
    
    def _get_provider(self):
        """Get or create the Gemini provider used for classification."""
        if self._provider is None:
            from src.providers.gemini import GeminiProvider

            self._provider = GeminiProvider()
        return self._provider

    def analyze_prompt(self, prompt: str) -> PromptAnalysis:
        """Delegate to rule-based router for analysis."""
        return self._fallback_router.analyze_prompt(prompt)

    async def _call_llm(self, prompt: str) -> str:
        """
        Ask the cheap model to grade this prompt.

        The prompt under classification is truncated to 1000 characters. The
        opening of a prompt is almost always enough to judge its difficulty,
        and truncating bounds the classification cost for very long inputs.
        """
        provider = self._get_provider()

        classification_prompt = self.CLASSIFICATION_PROMPT.format(prompt=prompt[:1000])

        response = await provider.generate(
            classification_prompt,
            self.settings.classifier_model,
        )
        self.last_response = response
        return response.text
    
    def _parse_classification(self, llm_response: str) -> tuple[DifficultyTier, str]:
        """Parse LLM response into tier and reason."""
        response = llm_response.strip().upper()
        
        # Try to parse CATEGORY|reason format
        if "|" in response:
            parts = response.split("|", 1)
            category = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else "LLM classification"
        else:
            # Just extract the category from the response
            category = response
            reason = "LLM classification"
        
        # Map to tier
        if "SIMPLE" in category:
            return DifficultyTier.SIMPLE, reason
        elif "COMPLEX" in category:
            return DifficultyTier.COMPLEX, reason
        else:
            return DifficultyTier.MEDIUM, reason
    
    async def classify(self, prompt: str, force_tier: Optional[str] = None) -> RoutingDecision:
        """
        Classify using LLM with fallback to rules.
        """
        # Handle forced tier
        if force_tier:
            tier = DifficultyTier(force_tier)
            return RoutingDecision(
                tier=tier,
                model=self.model_map[tier],
                reason=f"Forced to {force_tier} tier by request",
                confidence=1.0,
            )

        # Check for "best model" override before spending an API call on
        # classification -- this used to only exist in RuleBasedRouter, so it
        # was dead whenever use_llm_router=True (the default).
        if _best_model_override(prompt):
            self.last_used_fallback = False
            return RoutingDecision(
                tier=DifficultyTier.COMPLEX,
                model=self.model_map[DifficultyTier.COMPLEX],
                reason="User requested best/highest quality model",
                confidence=0.95,
            )

        try:
            # Call LLM for classification
            llm_response = await self._call_llm(prompt)
            tier, reason = self._parse_classification(llm_response)

            self.last_used_fallback = False
            self.last_error = None
            return RoutingDecision(
                tier=tier,
                model=self.model_map[tier],
                reason=f"LLM: {reason}",
                confidence=0.85,
            )
        except Exception as e:
            # Fallback to rule-based on any error. This is flagged rather than
            # silent: an eval run where the LLM quietly errored on every prompt
            # would otherwise report rule-based accuracy as the LLM's.
            self.last_used_fallback = True
            self.last_error = e
            print(f"⚠️ LLM classification failed, using rules: {e}")
            return await self._fallback_router.classify(prompt, force_tier)


def get_router() -> BaseRouter:
    """
    Get the singleton router instance.
    
    Uses LLMRouter if enabled in settings, otherwise RuleBasedRouter.
    """
    global _router, _rule_router
    
    settings = get_settings()
    
    if settings.use_llm_router:
        if _router is None or not isinstance(_router, LLMRouter):
            _router = LLMRouter()
        return _router
    else:
        if _rule_router is None:
            _rule_router = RuleBasedRouter()
        return _rule_router

