"""Access resolver service for evaluating JWT claims against policies.

This service is the core of Phase 4 access control, responsible for:
1. Evaluating JWT claims against active AccessPolicies
2. Resolving which ToolGroups an agent can access
3. Caching access decisions in Redis for performance
"""

import hashlib
import json
import logging
from typing import Any

from observability import agent_access_cache_hits, agent_access_cache_misses

from domain.models import ClaimMatcher
from domain.repositories import AccessPolicyDtoRepository, ToolGroupDtoRepository
from infrastructure.cache import RedisCacheService
from integration.models.access_policy_dto import AccessPolicyDto

logger = logging.getLogger(__name__)


class AccessResolver:
    """Resolves agent access rights based on JWT claims and access policies.

    This service implements a tiered caching strategy:
    1. Redis cache (shared across instances)
    2. MongoDB (source of truth via AccessPolicyDtoRepository)

    Access Resolution Logic:
    1. Hash the relevant JWT claims for cache key
    2. Check Redis cache for pre-computed access
    3. If cache miss, evaluate all active policies
    4. For each policy, check if ALL ClaimMatchers match (AND logic)
    5. If ANY policy matches, grant access to its allowed groups (OR logic)
    6. Cache the resolved group IDs
    7. Return the union of all matched groups
    """

    # Cache TTL in seconds (5 minutes by default)
    DEFAULT_CACHE_TTL = 300

    def __init__(
        self,
        policy_repository: AccessPolicyDtoRepository,
        group_repository: ToolGroupDtoRepository,
        cache: RedisCacheService | None = None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        """Initialize the access resolver.

        Args:
            policy_repository: Repository for accessing policies
            group_repository: Repository for accessing tool groups
            cache: Optional Redis cache service for access caching
            cache_ttl: Cache TTL in seconds (default: 300)
        """
        self._policy_repository = policy_repository
        self._group_repository = group_repository
        self._cache = cache
        self._cache_ttl = cache_ttl

    async def resolve_agent_access(
        self,
        claims: dict[str, Any],
        skip_cache: bool = False,
    ) -> set[str]:
        """Resolve which tool group IDs an agent can access based on JWT claims.

        Args:
            claims: Decoded JWT claims dictionary
            skip_cache: If True, bypass cache and evaluate fresh

        Returns:
            Set of tool group IDs the agent can access
        """
        # Generate cache key from claims
        claims_hash = self._hash_claims(claims)

        # Try cache first (unless skip_cache is set)
        if not skip_cache and self._cache:
            try:
                cached_groups = await self._cache.get_agent_access_cache(claims_hash)
                if cached_groups is not None:
                    logger.debug(f"Cache hit for access resolution: {len(cached_groups)} groups")
                    agent_access_cache_hits.add(1)
                    return cached_groups
                agent_access_cache_misses.add(1)
            except Exception as e:
                logger.warning(f"Cache read failed, falling back to DB: {e}")
                agent_access_cache_misses.add(1)

        # Evaluate policies from database
        allowed_groups = await self._evaluate_policies(claims)

        # Cache the result
        if self._cache:
            try:
                await self._cache.set_agent_access_cache(claims_hash, allowed_groups, ttl=self._cache_ttl)
                logger.debug(f"Cached access resolution: {len(allowed_groups)} groups")
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

        return allowed_groups

    async def _evaluate_policies(self, claims: dict[str, Any]) -> set[str]:
        """Evaluate all active policies against the given claims.

        Args:
            claims: Decoded JWT claims dictionary

        Returns:
            Set of allowed group IDs from all matching policies
        """
        allowed_groups: set[str] = set()

        # Get all active policies, sorted by priority (highest first)
        policies = await self._policy_repository.get_active_async()

        if not policies:
            logger.debug("No active access policies found")
            return allowed_groups

        logger.debug(f"Evaluating {len(policies)} active access policies")
        logger.debug(f"Claims available: {list(claims.keys())}")

        for policy in policies:
            if self._policy_matches_claims(policy, claims):
                logger.debug(f"Policy '{policy.name}' (priority={policy.priority}) matched claims")
                allowed_groups.update(policy.allowed_group_ids)
            else:
                logger.debug(f"Policy '{policy.name}' did NOT match claims")

        logger.debug(f"Access resolution complete: {len(allowed_groups)} groups allowed")
        return allowed_groups

    def _policy_matches_claims(self, policy: AccessPolicyDto, claims: dict[str, Any]) -> bool:
        """Check if a policy's matchers all match the given claims (AND logic).

        Args:
            policy: The access policy DTO to evaluate
            claims: Decoded JWT claims dictionary

        Returns:
            True if ALL matchers match, False otherwise
        """
        logger.debug(f"Evaluating policy '{policy.name}' with {len(policy.claim_matchers)} matchers")

        if not policy.claim_matchers:
            logger.debug(f"Policy '{policy.name}' has no matchers - returning False")
            return False

        # AND logic: all matchers must match
        for matcher_dict in policy.claim_matchers:
            try:
                matcher = ClaimMatcher.from_dict(matcher_dict)
                logger.debug(f"  Matcher: {matcher.json_path} {matcher.operator.value} '{matcher.value}'")
                if not matcher.matches(claims):
                    logger.debug(f"  -> Matcher did NOT match. Claim path '{matcher.json_path}' in claims: {claims.get(matcher.json_path.split('.')[0], 'NOT FOUND')}")
                    return False
                logger.debug("  -> Matcher matched!")
            except Exception as e:
                logger.warning(f"Failed to evaluate matcher in policy {policy.id}: {e}")
                return False

        return True

    def _hash_claims(self, claims: dict[str, Any]) -> str:
        """Generate a cache key hash from JWT claims.

        Only hashes fields that are relevant for access decisions,
        not volatile fields like 'exp', 'iat', 'jti'.

        Args:
            claims: Decoded JWT claims dictionary

        Returns:
            SHA256 hash of the relevant claims
        """
        # Fields to exclude from hashing (volatile/irrelevant)
        excluded_fields = {"exp", "iat", "jti", "nbf", "auth_time", "session_state", "nonce"}

        # Create a sorted, deterministic representation
        relevant_claims = {k: v for k, v in claims.items() if k not in excluded_fields}

        # Sort keys for deterministic hashing
        claims_str = json.dumps(relevant_claims, sort_keys=True, default=str)

        return hashlib.sha256(claims_str.encode()).hexdigest()[:32]

    async def invalidate_all_caches(self) -> int:
        """Invalidate all cached access decisions.

        Should be called when access policies change.

        Returns:
            Number of cache entries invalidated
        """
        if not self._cache:
            return 0

        try:
            count = await self._cache.invalidate_all_access_caches()
            logger.info(f"Invalidated {count} access cache entries")
            return count
        except Exception as e:
            logger.error(f"Failed to invalidate access caches: {e}")
            return 0

    async def get_accessible_groups(
        self,
        claims: dict[str, Any],
        include_inactive: bool = False,
    ) -> list[str]:
        """Get the list of accessible tool group IDs for the given claims.

        This is a convenience method that validates groups exist.

        Args:
            claims: Decoded JWT claims dictionary
            include_inactive: Whether to include inactive groups

        Returns:
            List of valid, accessible group IDs
        """
        # Resolve access from policies
        allowed_group_ids = await self.resolve_agent_access(claims)

        if not allowed_group_ids:
            return []

        # Validate that groups exist (and are active if requested)
        valid_groups = await self._group_repository.get_by_ids_async(list(allowed_group_ids))

        if include_inactive:
            return [g.id for g in valid_groups]
        else:
            return [g.id for g in valid_groups if g.is_active]
