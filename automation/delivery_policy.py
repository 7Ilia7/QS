"""Pure QS delivery decisions; no credentials, network or runtime data access."""
from release_lib import SHA, require

REPOSITORY = '7Ilia7/QS'
TERMINAL_PHASES = {'bootstrap_verified', 'activated_local_verified', 'already_current_verified'}


def delivery_context(event_name, event, repository, ref, auto_ready):
    require(repository.lower() == REPOSITORY.lower(), 'repository')
    if ref != 'refs/heads/main':
        return None
    if event_name == 'workflow_run':
        run = event.get('workflow_run', {})
        if not (auto_ready and event.get('action') == 'completed' and run.get('status') == 'completed'
                and run.get('conclusion') == 'success' and run.get('event') == 'push'
                and run.get('head_branch') == 'main' and run.get('name') == 'Website CI'
                and run.get('head_repository', {}).get('full_name', '').lower() == repository.lower()):
            return None
        require(type(run.get('id')) is int and run['id'] > 0, 'run_id')
        require(isinstance(run.get('head_sha'), str) and SHA.fullmatch(run['head_sha']), 'selected_SHA')
        return {'kind': 'automatic', 'source_sha': run['head_sha'], 'run_id': run['id'], 'expected_current': None}
    if event_name != 'workflow_dispatch' or ref != 'refs/heads/main':
        return None
    inputs = event.get('inputs', {})
    kind = inputs.get('action')
    require(kind in {'bootstrap', 'rollback'}, 'manual_action')
    require(not (kind == 'bootstrap' and auto_ready), 'bootstrap_already_enabled')
    sha, run_id = inputs.get('source_sha', ''), inputs.get('ci_run_id', '')
    require(SHA.fullmatch(sha) and run_id.isdecimal() and 0 < int(run_id) < 10**19, 'manual_identity')
    expected = inputs.get('expected_current') or None
    if kind == 'rollback':
        require(isinstance(expected, str) and SHA.fullmatch(expected), 'rollback_expected_current')
    return {'kind': kind, 'source_sha': sha, 'run_id': int(run_id), 'expected_current': expected}


def validate_delivery(value):
    require(isinstance(value, dict) and set(value) == {'kind', 'workflow_id', 'run_number', 'run_id'}, 'delivery_fields')
    require(value['kind'] in {'automatic', 'bootstrap', 'rollback'}, 'delivery_kind')
    require(all(type(value[k]) is int and 0 < value[k] < 10**19 for k in ['workflow_id', 'run_number', 'run_id']), 'delivery_run_identity')
    return value


def is_new_auto_run(delivery, previous):
    validate_delivery(delivery)
    require(previous is not None, 'bootstrap_not_registered')
    validate_delivery(previous)
    require(previous['workflow_id'] == delivery['workflow_id'], 'CI_workflow_identity_changed')
    return delivery['run_number'] > previous['run_number']


def selected_head_is_current(kind, selected, latest):
    require(isinstance(latest, str) and SHA.fullmatch(latest), 'main_head')
    return kind == 'rollback' or selected == latest
