# ==============================================================================
# BRANCH LEDGER: api (C000)
# ==============================================================================
#
# Classes (in file order):
#   - C001: ProjectResolutionEngine
#
# ------------------------------------------------------------------------------
# ## _normalize_strategy_configs(strategy_configs)
#    (Module ID: C000, Function ID: F001)
# ------------------------------------------------------------------------------
# C000F001B0001: strategy_configs is None -> return {} (empty dict)
# C000F001B0002: strategy_configs is not None AND for c in strategy_configs executes 0 times -> return {} (empty dict)
# C000F001B0003: for c in strategy_configs executes >= 1 time AND iid = c.get("instance_id", c.get("strategy_name")) is falsy -> raise ValueError("strategy config requires instance_id or strategy_name")
# C000F001B0004: for c in strategy_configs executes >= 1 time AND iid is truthy -> configs_by_instance_id[iid] stored with injected cfg["instance_id"] == iid, then return configs_by_instance_id
#
# ------------------------------------------------------------------------------
# ## _roots_for_env(params, env)
#    (Module ID: C000, Function ID: F002)
# ------------------------------------------------------------------------------
# C000F002B0001: for ws in params.root_wheels executes 0 times -> return [] (no ResolverRequirement created)
# C000F002B0002: for ws in params.root_wheels executes >= 1 time AND ws.marker is None -> append ResolverRequirement(wheel_spec=ws) (marker.evaluate not called) and return list including that ws
# C000F002B0003: for ws in params.root_wheels executes >= 1 time AND ws.marker is not None AND not ws.marker.evaluate(environment=marker_env) -> continue (ws excluded) and return list that does not include that ws
# C000F002B0004: for ws in params.root_wheels executes >= 1 time AND ws.marker is not None AND ws.marker.evaluate(environment=marker_env) -> append ResolverRequirement(wheel_spec=ws) and return list including that ws
#
# ------------------------------------------------------------------------------
# ## _wk_by_name_from_result(result)
#    (Module ID: C000, Function ID: F003)
# ------------------------------------------------------------------------------
# C000F003B0001: pinned_by_name.items() yields 0 items -> return {} (empty dict)
# C000F003B0002: pinned_by_name.items() yields >= 1 item -> return {name: cand.wheel_key for (name, cand) in pinned_by_name.items()}
#
# ------------------------------------------------------------------------------
# ## _deps_by_parent_from_result(result, wk_by_name)
#    (Module ID: C000, Function ID: F004)
# ------------------------------------------------------------------------------
# C000F004B0001: wk_by_name.keys() yields 0 items -> deps_by_parent initialized as {} (empty dict)
# C000F004B0002: wk_by_name.keys() yields >= 1 item -> deps_by_parent initialized with each key mapped to set()
# C000F004B0003: for (child_name, crit) in result.criteria.items() executes 0 times -> return deps_by_parent (as initialized)
# C000F004B0004: outer loop executes >= 1 time AND for info in crit.information executes 0 times -> no mutation for that child_name; eventual return deps_by_parent unchanged by that crit
# C000F004B0005: for info in crit.information executes >= 1 time AND parent = info.parent is None -> continue (skip this info)
# C000F004B0006: parent is not None AND (parent in deps_by_parent) is False -> no add (short-circuit; child_name in wk_by_name not evaluated) and proceed to next info
# C000F004B0007: parent is not None AND (parent in deps_by_parent) is True AND (child_name in wk_by_name) is False -> no add; deps_by_parent unchanged for this info
# C000F004B0008: parent is not None AND (parent in deps_by_parent) is True AND (child_name in wk_by_name) is True -> deps_by_parent[parent.name].add(child_name) mutates that parent's set
#
# ------------------------------------------------------------------------------
# ## _apply_dependency_ids(deps_by_parent, wk_by_name)
#    (Module ID: C000, Function ID: F005)
# ------------------------------------------------------------------------------
# C000F005B0001: for (parent_name, child_names) in deps_by_parent.items() executes 0 times -> no set_dependency_ids calls; return None
# C000F005B0002: loop executes >= 1 time AND sorted(child_names) yields 0 items -> call parent_wk.set_dependency_ids([]); return None
# C000F005B0003: loop executes >= 1 time AND sorted(child_names) yields >= 1 item -> call parent_wk.set_dependency_ids(dep_wks) where dep_wks order matches sorted(child_names); return None
#
# ------------------------------------------------------------------------------
# ## _format_requirements_text(wheel_keys)
#    (Module ID: C000, Function ID: F006)
# ------------------------------------------------------------------------------
# C000F006B0001: sorted(wheel_keys) yields 0 items -> return "\n"
# C000F006B0002: sorted(wheel_keys) yields >= 1 item -> return "\n\n".join(wk.req_txt_block for wk in sorted(wheel_keys)) + "\n"
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionEngine.resolve(params, *, debug=None)
#    (Class ID: C001, Method ID: M001)
# ------------------------------------------------------------------------------
# C001M001B0001: for env in params.target_environments executes 0 times -> load_services called once; no rl_resolve calls; return ResolutionResult(requirements_by_env={}, resolved_wheels_by_env={})
# C001M001B0002: for env in params.target_environments executes >= 1 time -> for each env.identifier, reqs_by_env[env.identifier] set to _format_requirements_text(list(wk_by_name.values())); return ResolutionResult with requirements_by_env containing those env identifiers
# C001M001B0003: params.resolution_mode is ResolutionMode.RESOLVED_WHEELS -> wheels_by_env[env.identifier] set to [] for each env processed; returned resolved_wheels_by_env contains those env identifiers
# C001M001B0004: params.resolution_mode is not ResolutionMode.RESOLVED_WHEELS -> wheels_by_env not populated for that env; returned resolved_wheels_by_env does not contain that env identifier
#
# ------------------------------------------------------------------------------
# LEDGER COMPLETENESS CHECKLIST
#   [x] all `if` / `elif` / `else` captured
#   [x] all `match` / `case` arms captured (none present)
#   [x] all `except` handlers captured (none present)
#   [x] all early `return`s / `raise`s / `yield`s captured
#   [x] all loop 0 vs >= 1 iterations captured
#   [x] all `break` / `continue` paths captured
# ==============================================================================
