"""Rule registration and discovery."""

from typing import Callable

from ebert.models import FocusArea
from ebert.rules.base import Rule

RuleFactory = Callable[[], Rule]

_rules: dict[str, RuleFactory] = {}


def register_rule(rule_id: str, factory: RuleFactory) -> None:
  """Register a rule factory.

  Args:
    rule_id: Unique identifier for the rule (e.g., 'SEC001').
    factory: Callable that returns a Rule instance.
  """
  _rules[rule_id] = factory


def get_all_rules() -> list[Rule]:
  """Get instances of all registered rules."""
  return [factory() for factory in _rules.values()]


def get_rules_for_focus(focus_areas: list[FocusArea]) -> list[Rule]:
  """Get rules matching specified focus areas.

  Args:
    focus_areas: List of focus areas to filter by.

  Returns:
    List of Rule instances matching the focus areas.
    Returns all rules if FocusArea.ALL is in the list.
  """
  if FocusArea.ALL in focus_areas:
    return get_all_rules()

  return [
    rule for rule in get_all_rules()
    if rule.focus_area in focus_areas
  ]


def list_rules() -> list[str]:
  """List all registered rule IDs."""
  return list(_rules.keys())


class RuleRegistry:
  """Registry for lazy rule loading."""

  @staticmethod
  def load_all() -> None:
    """Load all rule modules to trigger registration.

    Call this before using get_all_rules() or get_rules_for_focus()
    to ensure all rules are registered.
    """
    # Import rule modules here to trigger registration
    # Each module registers its rules at import time
    from ebert.rules.security import (
      credentials,  # noqa: F401
      merge_conflicts,  # noqa: F401
      secrets,  # noqa: F401
    )
