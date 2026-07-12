"""Product Creative project plugin."""

from __future__ import annotations

from pathlib import Path

from .infrastructure.composition import configure_default_repositories

configure_default_repositories()

from .cli import product_command, register_cli
from .capabilities.content.llm_service import configure_llm as configure_generator_llm
from .capabilities.inspiration.llm_service import configure_llm as configure_inspiration_llm
from .capabilities.learning.result_evaluation_service import configure_llm as configure_self_iteration_llm
from .runtime.decision_service import configure_llm as configure_decision_llm
from .tools import register_tools


def register(ctx) -> None:
    try:
        configure_generator_llm(ctx.llm)
        configure_inspiration_llm(ctx.llm)
        configure_self_iteration_llm(ctx.llm)
        configure_decision_llm(ctx.llm)
    except Exception:
        configure_generator_llm(None)
        configure_inspiration_llm(None)
        configure_self_iteration_llm(None)
        configure_decision_llm(None)
    register_tools(ctx)
    operator_skill = (
        Path(__file__).resolve().parent
        / "skills"
        / "product-creative-operator"
        / "SKILL.md"
    )
    if operator_skill.exists():
        ctx.register_skill(
            name="product-creative-operator",
            path=operator_skill,
            description=(
                "Operate Product Creative through Hermes conversation by "
                "preferring product_workflow_run for product-centered workflows."
            ),
        )
    ctx.register_cli_command(
        name="product",
        help="Product Creative workflows",
        setup_fn=register_cli,
        handler_fn=product_command,
        description=(
            "Create Product Wiki workspaces, generate copy packs, record "
            "feedback, and evolve Product Brain."
        ),
    )
