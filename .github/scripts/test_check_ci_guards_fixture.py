#!/usr/bin/env python3
from pathlib import Path


def write_repo(repo, script_file):
    workflows = repo / '.github' / 'workflows'
    setup_action = repo / '.github' / 'actions' / 'setup-windows-deps'
    profiling_action = repo / '.github' / 'actions' / 'build-x265-profiling'
    scripts = repo / '.github' / 'scripts'
    patches = repo / '.github' / 'patches'
    workflows.mkdir(parents=True)
    setup_action.mkdir(parents=True)
    profiling_action.mkdir(parents=True)
    scripts.mkdir(parents=True)
    patches.mkdir(parents=True)

    script_path = Path(script_file).resolve()
    github_dir = script_path.parents[1]

    workflow_files = (
        'build.yml',
        'build-profiling.yml',
        'build-pgo.yml',
        'update-deps.yml',
    )
    for name in workflow_files:
        (workflows / name).write_text((github_dir / 'workflows' / name).read_text())

    script_copies = (
        'check_ci_guards_data.py',
        'check_ci_guards_helpers.py',
        'check_ci_guards_checks.py',
        'check_dependency_patch_suffixes.py',
        'cxx20_scan_helpers.sh',
        'mp4_smoke_helpers.sh',
        'profiling_smoke_package_verify.sh',
        'verify_ci_archive.sh',
        'check_source_test_vectors.py',
        'test_check_source_test_vectors.py',
        'runtime_smoke_suite.sh',
        'mp4_smoke_suite.sh',
    )
    for name in script_copies:
        (scripts / name).write_text(script_path.with_name(name).read_text())

    (setup_action / 'action.yml').write_text((github_dir / 'actions' / 'setup-windows-deps' / 'action.yml').read_text())
    (profiling_action / 'action.yml').write_text((github_dir / 'actions' / 'build-x265-profiling' / 'action.yml').read_text())

    (repo / '.github' / 'deps-cache.json').write_text('''{
  "lsmash": "04e39f1fb232c332d4b04a1043c02c7c2d282d00",
  "obuparse": "v2.0.2",
  "gop_muxer": "5677cf5ef905c2412ed31de300cd1a08b341d21d"
}\n''')
    (patches / 'l-smash-clang-coff-refptr.patch').write_text('lsmash patch\n')
    (patches / 'gop-muxer-lsmash-add-box.patch').write_text('gop patch\n')


def replace_text(path, old, new, count=1):
    text = path.read_text()
    if old not in text:
        raise AssertionError(f'missing text {old!r} in {path}')
    path.write_text(text.replace(old, new, count))


def case(modifier, expected, check):
    return {
        'modifier': modifier,
        'expected': expected,
        'check': check,
    }
