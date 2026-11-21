"""
API Routes for Smart Model Router.

Defines all HTTP endpoints organized by functionality:
- /v1/complete: Main completion endpoint
- /v1/keys: API key management
- /health: Health check
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from src.api.dependencies import DBSession, ValidatedAPIKey, generate_api_key
from src.api.schemas import (
    APIKeyCreate,
    APIKeyListResponse,
    APIKeyResponse,
    CompletionRequest,
    CompletionResponse,
    ErrorResponse,
    HealthResponse,
    RouteRequest,
    RouteResponse,
    StructuredRequest,
    StructuredResponse,
)
from src.config import get_settings
from src.db import APIKey, get_session

# Create router for v1 API
router = APIRouter(prefix="/v1", tags=["v1"])


# ===================
# Hybrid router (Phase 5): POST /v1/route
# ===================

_phase5_router = None


def get_phase5_router():
    """Lazily built hybrid router (policy path from router.config / ROUTER_POLICY_PATH). Overridable in tests via
    app.dependency_overrides[get_phase5_router]."""
    global _phase5_router
    if _phase5_router is None:
        from router.pipeline import build_router
        _phase5_router = build_router()
    return _phase5_router


@router.post(
    "/route",
    response_model=RouteResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        503: {"model": ErrorResponse, "description": "Every step of the plan failed"},
    },
    summary="Route a task through the hybrid local/API router",
    description="Classifies the task, then tries solver -> local model (validated) -> paid API per the routing policy. "
                "Returns the answer plus category, layer, model, cost and savings vs the best single model (B1).",
)
async def route_task(
    request: RouteRequest,
    api_key: ValidatedAPIKey,
    session: DBSession,
    hybrid=Depends(get_phase5_router),
) -> RouteResponse:
    import hashlib
    import uuid

    from fastapi.concurrency import run_in_threadpool

    from router.logging import RequestLogger
    from src.db import DifficultyTag, RequestLog

    res = await run_in_threadpool(hybrid.route, request.prompt)
    request_id = uuid.uuid4().hex[:12]
    # 1) JSONL request log (router/logging.py); a logging failure never fails the request
    try:
        RequestLogger(hybrid.cfg.log_path).write(res, request_id=request_id)
    except Exception:  # noqa: BLE001
        pass
    # 2) existing request-log table (prompt stored as a hash only)
    try:
        tag = {"easy": DifficultyTag.SIMPLE, "hard": DifficultyTag.COMPLEX}.get(res.difficulty, DifficultyTag.MEDIUM)
        if res.category == "out_of_scope":
            tag = DifficultyTag.MEDIUM
        tin = sum((e.get("tokens_in") or 0) for e in res.trace if e.get("step") in ("api", "local"))
        tout = sum((e.get("tokens_out") or 0) for e in res.trace if e.get("step") in ("api", "local"))
        session.add(RequestLog(
            api_key_id=api_key.id, prompt_hash=hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
            prompt_length=len(request.prompt), difficulty_tag=tag, model_used=(res.model or "none")[:100],
            input_tokens=tin, output_tokens=tout, estimated_cost=res.cost_usd, baseline_cost=res.b1_cost_usd,
            cost_saved=res.savings_usd, latency_ms=res.latency_ms, cache_hit=False,
            response_hash=hashlib.sha256(res.answer.encode("utf-8")).hexdigest() if res.answer else None,
            error_message=res.error))
        await session.flush()
    except Exception:  # noqa: BLE001
        pass
    if res.layer == "error":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"All routing steps failed: {res.error}")
    return RouteResponse(answer=res.answer, category=res.category, difficulty=res.difficulty, layer=res.layer, model=res.model,
                         escalated=res.escalated, cost_usd=round(res.cost_usd, 8), b1_cost_usd=round(res.b1_cost_usd, 8),
                         savings_usd=round(res.savings_usd, 8), latency_ms=res.latency_ms, trace=res.trace)


# ===================
# Completion Endpoint
# ===================

@router.post(
    "/complete",
    response_model=CompletionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="(legacy) Generate a completion",
    description="LEGACY: the original three-tier Gemini difficulty router, kept for compatibility. Use POST /v1/route. "
                "Routes the prompt to the most cost-effective model based on complexity.",
    deprecated=True,
)
async def create_completion(
    request: CompletionRequest,
    api_key: ValidatedAPIKey,
    session: DBSession,
) -> CompletionResponse:
    """
    Main completion endpoint.
    
    Flow:
    1. Validate API key (via dependency)
    2. Check cache for existing response (semantic or exact match)
    3. Classify prompt difficulty
    4. Route to appropriate model
    5. Cache the response
    6. Log request and cost
    7. Return response with cost data
    """
    import time
    from src.config import get_settings
    from src.core import get_router
    from src.providers import get_provider_manager, ProviderError
    from src.services import (
        get_cost_calculator, 
        get_request_logger, 
        get_cache_service,
        get_semantic_cache_service,
        CachedResponse,
        SemanticCachedResponse,
    )
    
    start_time = time.perf_counter()
    settings = get_settings()
    
    # Step 1: Check cache first (semantic or exact based on config)
    if settings.use_semantic_cache:
        semantic_cache = get_semantic_cache_service()
        cached = await semantic_cache.get(request.prompt)
        if cached:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return CompletionResponse(
                response=cached.text,
                model_used=cached.model,
                difficulty_tag=cached.difficulty_tag,
                estimated_cost=cached.estimated_cost,
                estimated_savings=cached.estimated_savings,
                latency_ms=latency_ms,
                cache_hit=True,
            )
    else:
        cache_service = get_cache_service()
        cached = await cache_service.get(request.prompt)
        if cached:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return CompletionResponse(
                response=cached.text,
                model_used=cached.model,
                difficulty_tag=cached.difficulty_tag,
                estimated_cost=cached.estimated_cost,
                estimated_savings=cached.estimated_savings,
                latency_ms=latency_ms,
                cache_hit=True,
            )
    
    # Step 2: Classify the prompt
    router_agent = get_router()
    routing_decision = await router_agent.classify(
        request.prompt,
        force_tier=request.force_tier,
    )
    
    # Step 3: Call the appropriate model
    provider_manager = get_provider_manager()
    
    try:
        response, actual_tier = await provider_manager.generate(
            prompt=request.prompt,
            tier=routing_decision.tier,
            max_retries=2,
            allow_fallback=True,
        )
    except ProviderError as e:
        # Convert provider error to HTTP error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM provider error: {e}",
        )
    
    # Step 4: Calculate costs
    calculator = get_cost_calculator()
    cost_estimate = calculator.estimate(
        model=response.model,
        input_tokens=response.prompt_tokens,
        output_tokens=response.completion_tokens,
    )
    
    # Step 5: Cache the response
    if settings.use_semantic_cache:
        await semantic_cache.set(
            request.prompt,
            SemanticCachedResponse(
                text=response.text,
                model=response.model,
                difficulty_tag=actual_tier.value,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                estimated_cost=round(cost_estimate.estimated_cost, 6),
                estimated_savings=round(cost_estimate.savings, 6),
                original_prompt=request.prompt,
            ),
        )
    else:
        await cache_service.set(
            request.prompt,
            CachedResponse(
                text=response.text,
                model=response.model,
                difficulty_tag=actual_tier.value,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                estimated_cost=round(cost_estimate.estimated_cost, 6),
                estimated_savings=round(cost_estimate.savings, 6),
            ),
        )
    
    # Step 6: Log request to database
    logger = get_request_logger()
    await logger.log_request(
        session=session,
        api_key_id=api_key.id,
        prompt=request.prompt,
        response_text=response.text,
        provider_response=response,
        tier=actual_tier,
        cache_hit=False,
    )
    
    # Calculate latency (includes all processing)
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    return CompletionResponse(
        response=response.text,
        model_used=response.model,
        difficulty_tag=actual_tier.value,
        estimated_cost=round(cost_estimate.estimated_cost, 6),
        estimated_savings=round(cost_estimate.savings, 6),
        latency_ms=latency_ms,
        cache_hit=False,
    )


# ===================
# Structured Output Endpoint
# ===================

@router.post(
    "/structure",
    response_model=StructuredResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="(legacy) Generate structured JSON output",
    deprecated=True,
    description="Returns guaranteed structured JSON conforming to the provided schema using Gemini Flash.",
)
async def create_structured_output(
    request: StructuredRequest,
    api_key: ValidatedAPIKey,
) -> StructuredResponse:
    """
    Generate structured JSON output.
    
    Uses Gemini's responseSchema feature for guaranteed JSON conforming to schema.
    Always uses Gemini Flash for optimal speed/cost balance.
    No caching - structured outputs are request-specific.
    """
    import time
    from src.providers.gemini import GeminiProvider
    from src.services import get_cost_calculator
    
    start_time = time.perf_counter()
    settings = get_settings()
    
    # Always use Gemini Flash for structured output
    model = settings.tier_medium_model
    
    # Initialize Gemini provider
    provider = GeminiProvider()
    
    try:
        # Call Gemini with structured output
        data, prompt_tokens, completion_tokens, _ = await provider.generate_structured(
            prompt=request.prompt,
            json_schema=request.json_schema,
            model=model,
            system_prompt=request.system_prompt,
        )
        
        # Calculate cost
        calculator = get_cost_calculator()
        cost_estimate = calculator.estimate(
            model=model,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
        )
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        return StructuredResponse(
            data=data,
            model_used=model,
            estimated_cost=round(cost_estimate.estimated_cost, 6),
            latency_ms=latency_ms,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Structured output error: {str(e)}",
        )


# ===================
# API Key Management
# ===================

@router.post(
    "/keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="Generate a new API key. The raw key is only shown once!",
)
async def create_api_key(
    request: APIKeyCreate,
    session: DBSession,
) -> APIKeyResponse:
    """
    Create a new API key.
    
    WARNING: The raw key is only returned once. Store it securely!
    """
    # Generate key and hash
    raw_key, key_hash = generate_api_key()
    
    # Create database record
    api_key = APIKey(
        key_hash=key_hash,
        name=request.name,
        is_active=True,
    )
    session.add(api_key)
    await session.flush()  # Get the ID without committing
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,  # Only time we return the raw key!
        is_active=api_key.is_active,
        created_at=api_key.created_at or datetime.now(timezone.utc),
        last_used_at=api_key.last_used_at,
    )


@router.get(
    "/keys",
    response_model=APIKeyListResponse,
    summary="List all API keys",
    description="List all API keys (without the raw key values).",
)
async def list_api_keys(
    session: DBSession,
) -> APIKeyListResponse:
    """List all API keys."""
    result = await session.execute(
        select(APIKey).order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    
    return APIKeyListResponse(
        keys=[
            APIKeyResponse(
                id=key.id,
                name=key.name,
                key=None,  # Never expose raw key in list
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
            )
            for key in keys
        ],
        total=len(keys),
    )


@router.delete(
    "/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate an API key",
    description="Deactivate an API key (soft delete).",
)
async def deactivate_api_key(
    key_id: str,
    session: DBSession,
) -> None:
    """Deactivate an API key (soft delete)."""
    from uuid import UUID
    
    try:
        uuid_key = UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format",
        )
    
    result = await session.execute(
        select(APIKey).where(APIKey.id == uuid_key)
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    api_key.is_active = False
