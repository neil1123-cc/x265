#!/usr/bin/env python3
import re
from pathlib import Path

import check_ci_guards_data as data_module


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_REFERENCE = re.compile(r'\b(?:python|bash)\s+([A-Za-z0-9_./-]+\.(?:py|sh))\b')
REQUIREMENT_FUNCTIONS = (
    data_module.build_step_requirements,
    data_module.profiling_step_requirements,
    data_module.pgo_step_requirements,
)
CI_REFERENCE_FILES = (
    Path('.github/scripts/check_ci_guards.py'),
    Path('.github/scripts/check_ci_guards_data.py'),
    Path('.github/scripts/run_python_ci_guard_bundle.py'),
    Path('.github/workflows/build.yml'),
    Path('.github/workflows/build-profiling.yml'),
    Path('.github/workflows/build-pgo.yml'),
    Path('.github/workflows/update-deps.yml'),
)
NON_EXECUTED_TEST_FILES = {
    'test_check_ci_guards_fixture.py',
}


def normalize_repo_relative(script_path):
    path = Path(script_path)
    parts = path.parts
    if parts[:2] == ('..', 'x265'):
        parts = parts[2:]
    elif parts[:1] == ('x265',):
        parts = parts[1:]
    return Path(*parts)


def assert_path_constants_exist():
    checked = 0
    missing = []
    for name, value in vars(data_module).items():
        if not (name.isupper() and isinstance(value, Path)):
            continue
        checked += 1
        path = REPO_ROOT / value
        if not path.exists():
            missing.append(f'{name} -> {value.as_posix()}')
    if checked == 0:
        raise AssertionError('expected Path constants in check_ci_guards_data.py')
    if missing:
        raise AssertionError('missing data-module paths:\n' + '\n'.join(sorted(missing)))


def iter_requirement_entries():
    for requirement_fn in REQUIREMENT_FUNCTIONS:
        requirements = requirement_fn()
        if not requirements:
            raise AssertionError(f'{requirement_fn.__name__} returned no requirements')
        for entry in requirements:
            if not isinstance(entry, tuple) or len(entry) != 3:
                raise AssertionError(f'{requirement_fn.__name__} returned malformed entry: {entry!r}')
            yield requirement_fn.__name__, entry


def assert_requirement_shapes():
    total_entries = 0
    for requirement_name, entry in iter_requirement_entries():
        total_entries += 1
        job_name, step_name, required_items = entry
        if not isinstance(job_name, str) or not job_name.strip():
            raise AssertionError(f'{requirement_name} has invalid job name: {entry!r}')
        if not isinstance(step_name, str) or not step_name.strip():
            raise AssertionError(f'{requirement_name} has invalid step name: {entry!r}')
        if not isinstance(required_items, tuple) or not required_items:
            raise AssertionError(f'{requirement_name} has invalid required-items tuple: {entry!r}')
        for required in required_items:
            if not isinstance(required, str) or not required.strip():
                raise AssertionError(f'{requirement_name} contains invalid required item: {entry!r}')
    if total_entries == 0:
        raise AssertionError('expected at least one CI guard requirement entry')


def assert_requirement_script_references_exist():
    referenced = set()
    missing = []
    for requirement_name, entry in iter_requirement_entries():
        _, _, required_items = entry
        for required in required_items:
            for match in SCRIPT_REFERENCE.finditer(required):
                script = normalize_repo_relative(match.group(1))
                if not script.parts:
                    continue
                referenced.add(script.as_posix())
                if not (REPO_ROOT / script).is_file():
                    missing.append(f'{requirement_name}: {script.as_posix()} referenced by {required!r}')
    if not referenced:
        raise AssertionError('expected requirement entries to reference CI guard scripts')
    if missing:
        raise AssertionError('missing scripts referenced by CI guard requirements:\n' + '\n'.join(sorted(missing)))


def assert_all_guard_tests_are_referenced():
    ci_blob_parts = []
    referenced = set()
    for rel in CI_REFERENCE_FILES:
        text = (REPO_ROOT / rel).read_text(encoding='utf-8', errors='ignore')
        ci_blob_parts.append(text)
        for match in SCRIPT_REFERENCE.finditer(text):
            script = normalize_repo_relative(match.group(1))
            if script.parts:
                referenced.add(script.name)
    ci_blob = '\n'.join(ci_blob_parts)
    missing = []
    for test in sorted((REPO_ROOT / '.github/scripts').glob('test_check_*.py')):
        if test.name in NON_EXECUTED_TEST_FILES:
            continue
        if test.name not in referenced and test.name not in ci_blob:
            missing.append(test.name)
    if missing:
        raise AssertionError('CI is missing references to guard tests:\n' + '\n'.join(missing))


def main():
    assert_path_constants_exist()
    assert_requirement_shapes()
    assert_requirement_script_references_exist()
    assert_all_guard_tests_are_referenced()
    print('CI guard data tests passed')


if __name__ == '__main__':
    main()
