#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scenecut_trailing_arg_diagnostics.py')

# Coverage probes used by the scan for scenecut trailing-argument diagnostics.
NORMALIZED_PROBES = (
    'missing scenecut trailing-arg diagnostic guardrail: ',
    'scenecut trailing-arg diagnostics must stay attached to the correct parser layer',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'bool CLIOptions::parse(int argc, char **argv)',
                    '{',
                    '    x265_log(param, X265_LOG_WARNING, "extra unused command arguments given <%s>\\n", argv[optind]);',
                    '}',
                    'bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'bool CLIOptions::parse(int argc, char **argv)\n{\n    x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);\n}\n',
            },
        )
        expect_fail(run_checker(root), 'missing scenecut trailing-arg diagnostic guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'bool CLIOptions::parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam)',
                    '{',
                    '    x265_log(param, X265_LOG_WARNING, "extra unused command arguments given <%s>\\n", argv[optind]);',
                    '}',
                    'bool CLIOptions::parse(int argc, char **argv)',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "extra unused scenecut-aware QP config arguments given <%s>\\n", argv[optind]);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI and nested scenecut trailing-arg diagnostics must both be present')

    print('Scenecut trailing-arg diagnostic tests passed')


if __name__ == '__main__':
    main()
