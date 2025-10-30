"""
Feature flags implementation for gradual rollout and A/B testing.
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class RolloutStrategy(Enum):
    """Rollout strategy types."""
    PERCENTAGE = "percentage"
    USER_ATTRIBUTE = "user_attribute"
    ENVIRONMENT = "environment"
    CANARY = "canary"


@dataclass
class RolloutRule:
    """Rollout rule configuration."""
    name: str
    percentage: int
    conditions: list[dict[str, Any]]
    strategy: RolloutStrategy = RolloutStrategy.PERCENTAGE


@dataclass
class FeatureFlag:
    """Feature flag configuration."""
    name: str
    enabled: bool
    rollout_percentage: int
    description: str
    variants: Optional[dict[str, int]] = None
    rollout_rules: Optional[list[RolloutRule]] = None


class FeatureFlagManager:
    """
    Feature flag manager for controlling feature rollouts.

    Supports:
    - Percentage-based rollouts
    - User attribute-based targeting
    - Environment-based rules
    - A/B testing variants
    """

    def __init__(self, config_source: str = "configmap"):
        """
        Initialize feature flag manager.

        Args:
            config_source: Source of configuration ("configmap", "file", "env")
        """
        self.config_source = config_source
        self.flags: dict[str, FeatureFlag] = {}
        self.rollout_rules: list[RolloutRule] = []
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load feature flag configuration from source."""
        try:
            if self.config_source == "configmap":
                self._load_from_configmap()
            elif self.config_source == "file":
                self._load_from_file()
            elif self.config_source == "env":
                self._load_from_environment()
            else:
                logger.warning(f"Unknown config source: {self.config_source}")

        except Exception as e:
            logger.error(f"Failed to load feature flag configuration: {e}")
            # Use default configuration
            self._load_defaults()

    def _load_from_configmap(self) -> None:
        """Load configuration from Kubernetes ConfigMap."""
        config_path = "/app/config/flags.yaml"
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = yaml.safe_load(f)
                self._parse_configuration(config)
        else:
            logger.warning("ConfigMap not found, using defaults")
            self._load_defaults()

    def _load_from_file(self) -> None:
        """Load configuration from file."""
        config_path = os.getenv("FEATURE_FLAGS_CONFIG", "feature_flags.yaml")
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = yaml.safe_load(f)
                self._parse_configuration(config)
        else:
            self._load_defaults()

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Simple environment-based configuration
        self.flags = {
            "multi_timeframe_analysis": FeatureFlag(
                name="multi_timeframe_analysis",
                enabled=os.getenv("FF_MULTI_TIMEFRAME", "true").lower() == "true",
                rollout_percentage=int(os.getenv("FF_MULTI_TIMEFRAME_PCT", "100")),
                description="Multi-timeframe analysis"
            ),
            "llm_routing": FeatureFlag(
                name="llm_routing",
                enabled=os.getenv("FF_LLM_ROUTING", "true").lower() == "true",
                rollout_percentage=int(os.getenv("FF_LLM_ROUTING_PCT", "100")),
                description="Multi-LLM routing"
            ),
        }

    def _parse_configuration(self, config: dict[str, Any]) -> None:
        """Parse configuration dictionary."""
        flags_config = config.get("flags", {})

        for flag_name, flag_config in flags_config.items():
            self.flags[flag_name] = FeatureFlag(
                name=flag_name,
                enabled=flag_config.get("enabled", False),
                rollout_percentage=flag_config.get("rollout_percentage", 0),
                description=flag_config.get("description", ""),
                variants=flag_config.get("variants")
            )

        # Parse rollout rules
        rollout_rules_config = config.get("rollout_rules", [])
        for rule_config in rollout_rules_config:
            self.rollout_rules.append(RolloutRule(
                name=rule_config["name"],
                percentage=rule_config["percentage"],
                conditions=rule_config["conditions"]
            ))

    def _load_defaults(self) -> None:
        """Load default feature flag configuration."""
        self.flags = {
            "multi_timeframe_analysis": FeatureFlag(
                name="multi_timeframe_analysis",
                enabled=True,
                rollout_percentage=100,
                description="Enable multi-timeframe analysis"
            ),
            "llm_routing": FeatureFlag(
                name="llm_routing",
                enabled=True,
                rollout_percentage=100,
                description="Enable multi-LLM routing"
            ),
            "adaptive_position_sizing": FeatureFlag(
                name="adaptive_position_sizing",
                enabled=True,
                rollout_percentage=50,
                description="Enable adaptive position sizing"
            ),
        }

    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> bool:
        """
        Check if a feature flag is enabled for the given context.

        Args:
            flag_name: Name of the feature flag
            user_id: User identifier for consistent rollout
            context: Additional context for rule evaluation

        Returns:
            True if feature is enabled, False otherwise
        """
        flag = self.flags.get(flag_name)
        if not flag:
            logger.warning(f"Unknown feature flag: {flag_name}")
            return False

        if not flag.enabled:
            return False

        # Check rollout percentage
        if flag.rollout_percentage < 100:
            if not self._is_in_rollout(flag_name, flag.rollout_percentage, user_id):
                return False

        # Check rollout rules
        if context:
            for rule in self.rollout_rules:
                if self._evaluate_rule(rule, context):
                    return self._is_in_rollout(
                        f"{flag_name}_{rule.name}",
                        rule.percentage,
                        user_id
                    )

        return True

    def get_variant(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get the variant for a feature flag (for A/B testing).

        Args:
            flag_name: Name of the feature flag
            user_id: User identifier for consistent variant assignment
            context: Additional context for rule evaluation

        Returns:
            Variant name or None if flag is disabled
        """
        if not self.is_enabled(flag_name, user_id, context):
            return None

        flag = self.flags.get(flag_name)
        if not flag or not flag.variants:
            return "default"

        # Consistent variant assignment based on user_id
        hash_input = f"{flag_name}:{user_id or 'anonymous'}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        percentage = hash_value % 100

        cumulative = 0
        for variant, weight in flag.variants.items():
            cumulative += weight
            if percentage < cumulative:
                return variant

        return "default"

    def _is_in_rollout(
        self,
        key: str,
        percentage: int,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Determine if user is in rollout based on percentage.

        Args:
            key: Key for consistent hashing
            percentage: Rollout percentage (0-100)
            user_id: User identifier

        Returns:
            True if user is in rollout
        """
        if percentage >= 100:
            return True
        if percentage <= 0:
            return False

        hash_input = f"{key}:{user_id or 'anonymous'}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        return (hash_value % 100) < percentage

    def _evaluate_rule(self, rule: RolloutRule, context: dict[str, Any]) -> bool:
        """
        Evaluate if a rollout rule matches the given context.

        Args:
            rule: Rollout rule to evaluate
            context: Context to evaluate against

        Returns:
            True if rule matches
        """
        for condition in rule.conditions:
            attribute = condition["attribute"]
            operator = condition["operator"]
            expected_value = condition["value"]

            actual_value = context.get(attribute)

            if operator == "equals" and actual_value != expected_value:
                return False
            elif operator == "not_equals" and actual_value == expected_value:
                return False
            elif operator == "in" and actual_value not in expected_value:
                return False
            elif operator == "not_in" and actual_value in expected_value:
                return False

        return True

    def get_all_flags(self) -> dict[str, FeatureFlag]:
        """Get all feature flags."""
        return self.flags.copy()

    def reload_configuration(self) -> None:
        """Reload feature flag configuration."""
        self._load_configuration()
        logger.info("Feature flag configuration reloaded")


# Global feature flag manager instance
feature_flags = FeatureFlagManager()


def is_feature_enabled(
    flag_name: str,
    user_id: Optional[str] = None,
    context: Optional[dict[str, Any]] = None
) -> bool:
    """
    Convenience function to check if a feature is enabled.

    Args:
        flag_name: Name of the feature flag
        user_id: User identifier
        context: Additional context

    Returns:
        True if feature is enabled
    """
    return feature_flags.is_enabled(flag_name, user_id, context)


def get_feature_variant(
    flag_name: str,
    user_id: Optional[str] = None,
    context: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """
    Convenience function to get feature variant.

    Args:
        flag_name: Name of the feature flag
        user_id: User identifier
        context: Additional context

    Returns:
        Variant name or None
    """
    return feature_flags.get_variant(flag_name, user_id, context)


# Alias for backward compatibility
FeatureFlags = FeatureFlagManager
