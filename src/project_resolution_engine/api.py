from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, cast

from resolvelib.resolvers import Result

from project_resolution_engine.internal.resolvelib_types import ResolverCandidate
from project_resolution_engine.model.keys import WheelKey
from project_resolution_engine.model.resolution import (
    ResolutionMode,
    ResolutionParams,
    ResolutionResult,
    WheelSpec,
    ResolutionEnv,
)
from project_resolution_engine.services import load_services
from project_resolution_engine.strategies import ResolutionStrategyConfig


def _normalize_strategy_configs(
    strategy_configs: Iterable[ResolutionStrategyConfig] | None,
) -> dict[str, ResolutionStrategyConfig]:
    """
    Normalizes a collection of resolution strategy configurations into a dictionary
    indexed by instance ID or strategy name.

    This function processes a given iterable of resolution strategy configurations,
    extracting a unique identifier (either `instance_id` or `strategy_name`) for each
    configuration. It ensures that the resulting dictionary contains well-structured and
    indexed configurations for further usage.

    Args:
        strategy_configs (Iterable[ResolutionStrategyConfig] | None): An iterable containing
            resolution strategy configuration objects. Each configuration must have
            a valid `instance_id` or `strategy_name`. If `None`, an empty dictionary is
            returned.

    Returns:
        dict[str, ResolutionStrategyConfig]: A dictionary where the keys are instance IDs
        or strategy names, and the values are the corresponding resolution strategy
        configuration objects.

    Raises:
        ValueError: If any configuration in the provided collection lacks both `instance_id`
        and `strategy_name`.
    """
    configs_by_instance_id: dict[str, ResolutionStrategyConfig] = {}
    if strategy_configs is None:
        return configs_by_instance_id

    c: ResolutionStrategyConfig
    for c in strategy_configs:
        iid = c.get("instance_id", c.get("strategy_name"))
        if not iid:
            raise ValueError("strategy config requires instance_id or strategy_name")

        cfg = dict(c)
        cfg["instance_id"] = iid
        configs_by_instance_id[iid] = cast(ResolutionStrategyConfig, cast(object, cfg))

    return configs_by_instance_id


def _roots_for_env(params: ResolutionParams, env: Any) -> list[Any]:
    """
    Generates a list of ResolverRequirement objects filtered and derived from
    the provided `params` based on the compatibility with the given `env`.

    This function filters the root wheels in `params` by evaluating their
    associated markers against the `env.marker_environment`. Only those
    root wheels with markers that evaluate to True or have no markers
    are included in the root requirements.

    Args:
        params (ResolutionParams): Parameters containing root wheels, which
            are the sources to be converted into ResolverRequirement objects.
        env (Any): The environment against which root wheel markers are
            evaluated. Must provide a `marker_environment` attribute as a
            dictionary.

    Returns:
        list[Any]: A list of ResolverRequirement objects that meet the
        evaluated conditions.
    """
    from project_resolution_engine.internal.resolvelib_types import ResolverRequirement

    roots: list[ResolverRequirement] = []
    ws: WheelSpec
    for ws in params.root_wheels:
        marker_env = cast(dict[str, str], cast(object, env.marker_environment))
        if ws.marker is not None and not ws.marker.evaluate(environment=marker_env):
            continue
        roots.append(ResolverRequirement(wheel_spec=ws))

    return roots


def _wk_by_name_from_result(
    result: Result[Any, ResolverCandidate, str],
) -> dict[str, WheelKey]:
    """
    Converts the result mapping into a dictionary mapping names to WheelKeys.

    This function takes the `result` containing mapping data and processes it to extract
    a dictionary where each name is associated with its corresponding WheelKey.

    Args:
        result (Result[Any, ResolverCandidate, str]): The result object containing
            a `mapping` property, which holds a dictionary mapping names to
            `ResolverCandidate` instances.

    Returns:
        dict[str, WheelKey]: A dictionary mapping each name (str) to its associated
        `WheelKey`.
    """
    pinned_by_name: dict[str, ResolverCandidate] = result.mapping
    return {name: cand.wheel_key for name, cand in pinned_by_name.items()}


def _deps_by_parent_from_result(
    result: Result[Any, ResolverCandidate, str], wk_by_name: Mapping[str, WheelKey]
) -> dict[str, set[str]]:
    """
    Generate a mapping of parent items to their dependent child items based on the given resolution result
    and wheel keys.

    This function processes the resolution criteria to determine relationships between parent and child
    items. For each child item in the resolution criteria, it identifies its associated parent items
    and adds it to the tracking dictionary if both the parent and child exist in the input wheel key
    mapping.

    Args:
        result: The resolution result containing criteria and dependency information. Each criterion
            provides details about the dependencies and their relationships.
        wk_by_name: A mapping of names to their corresponding wheel keys, representing available
            resolved items.

    Returns:
        A dictionary where the keys are parent names and the values are sets of dependent child names.
        Parents with no children will have an empty set as the value.
    """
    deps_by_parent: dict[str, set[str]] = {name: set() for name in wk_by_name.keys()}

    child_name: str
    for child_name, crit in result.criteria.items():
        for info in crit.information:
            parent = info.parent
            if parent is None:
                continue
            # Preserve existing membership logic exactly.
            if parent in deps_by_parent and child_name in wk_by_name:
                deps_by_parent[parent.name].add(child_name)

    return deps_by_parent


def _apply_dependency_ids(
    deps_by_parent: Mapping[str, set[str]], wk_by_name: Mapping[str, WheelKey]
) -> None:
    """
    Applies dependency IDs to parent WheelKey objects based on their dependencies.

    This function associates each parent WheelKey object with its respective
    child dependencies (WheelKey objects), determined from the mapping of parent
    names to child names. Dependency IDs are then set on the parent WheelKey
    objects.

    Args:
        deps_by_parent (Mapping[str, set[str]]): A mapping where each key is the
            name of a parent entity, and the corresponding value is a set of
            names representing its child dependencies.
        wk_by_name (Mapping[str, WheelKey]): A mapping where each key is the name
            of an entity, and the corresponding value is a WheelKey object
            representing that entity.

    Returns:
        None
    """
    parent_wk: WheelKey
    for parent_name, child_names in deps_by_parent.items():
        parent_wk = wk_by_name[parent_name]
        dep_wks = [wk_by_name[n] for n in sorted(child_names)]
        parent_wk.set_dependency_ids(dep_wks)


def _format_requirements_text(wheel_keys: Iterable[WheelKey]) -> str:
    """
    Formats the requirements text by sorting the given wheel keys and combining their
    requirement text blocks into a single string.

    Args:
        wheel_keys (Iterable[WheelKey]): An iterable of WheelKey objects that contain
            the requirement text blocks to format.

    Returns:
        str: A formatted string representing the concatenated requirement text blocks
            of the provided wheel keys, separated by double newlines, and ending with
            a newline character.
    """
    return "\n\n".join(wk.req_txt_block for wk in sorted(wheel_keys)) + "\n"


@dataclass(kw_only=True, frozen=True, slots=True)
class ProjectResolutionEngine:
    """
    Represents a project resolution engine using strategies and repository configurations.

    This class is designed to handle the resolution process for a given set of parameters.
    It normalizes strategy configurations, interacts with repositories for loading services,
    and resolves dependencies for specified target environments. The resolution process
    produces requirements and resolved wheels categorized by environment.

    Methods:
        resolve(params: ResolutionParams) -> ResolutionResult
            Resolves dependencies based on the provided parameters, producing requirements
            and resolved wheels categorized by the target environments.
    """

    @staticmethod
    # :: FeatureFlow | type=feature_start | name=full_resolution
    def resolve(params: ResolutionParams) -> ResolutionResult:
        from project_resolution_engine.internal.resolvelib import resolve as rl_resolve
        from project_resolution_engine.internal.repositories.factory import (
            open_repository,
        )

        reqs_by_env: dict[str, str] = {}
        wheels_by_env: dict[str, list[str]] = {}

        configs_by_instance_id = _normalize_strategy_configs(params.strategy_configs)

        with open_repository(repo_id=params.repo_id, config=params.repo_config) as repo:
            services = load_services(
                repo=repo, strategy_configs_by_instance_id=configs_by_instance_id
            )

            env: ResolutionEnv
            for env in params.target_environments:
                roots = _roots_for_env(params, env)

                result: Result[Any, ResolverCandidate, str] = rl_resolve(
                    services=services, env=env, roots=roots
                )

                wk_by_name = _wk_by_name_from_result(result)
                deps_by_parent = _deps_by_parent_from_result(result, wk_by_name)
                _apply_dependency_ids(deps_by_parent, wk_by_name)

                wheel_keys: list[WheelKey] = list(wk_by_name.values())
                reqs_by_env[env.identifier] = _format_requirements_text(wheel_keys)

                if params.resolution_mode is ResolutionMode.RESOLVED_WHEELS:
                    # You currently never populate URIs here. Leaving behavior unchanged.
                    wheels_by_env[env.identifier] = []

        return ResolutionResult(
            requirements_by_env=reqs_by_env, resolved_wheels_by_env=wheels_by_env
        )
