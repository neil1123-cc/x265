#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_release_needs.py')


BUILD_NEEDS = '''
  publish-release:
    needs:
      - cxx20-warning-scan
      - cxx20-gcc-compile-commands
      - cxx20-linux-gcc-compile-commands
      - build-metadata
      - build
    if: startsWith(github.ref, 'refs/tags/')
'''


PROFILING_NEEDS = '''
  publish-release:
    needs: [build, validate-guardrails]
    if: startsWith(github.ref, 'refs/tags/')
'''


def run(*paths):
    return subprocess.run(
        [sys.executable, str(CHECKER), *(str(path) for path in paths)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def write_workflow(path, body):
    path.write_text(f'name: Test\njobs:\n{body}')


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
        build = root / 'build.yml'
        profiling = root / 'build-profiling.yml'
        pgo = root / 'build-pgo.yml'
        write_workflow(build, BUILD_NEEDS)
        write_workflow(profiling, PROFILING_NEEDS)
        write_workflow(pgo, '  generate:\n    runs-on: ubuntu-latest\n')
        expect_pass(run(build, profiling, pgo))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build = root / 'build.yml'
        write_workflow(build, BUILD_NEEDS.replace('      - cxx20-linux-gcc-compile-commands\n', ''))
        expect_fail(run(build), 'publish-release missing needs: cxx20-linux-gcc-compile-commands')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profiling = root / 'build-profiling.yml'
        write_workflow(profiling, PROFILING_NEEDS.replace('needs: [build, validate-guardrails]', 'needs: build'))
        expect_fail(run(profiling), 'publish-release missing needs: validate-guardrails')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build = root / 'build.yml'
        write_workflow(
            build,
            BUILD_NEEDS.replace(
                "if: startsWith(github.ref, 'refs/tags/')",
                "if: github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')",
            ),
        )
        expect_fail(run(build), 'publish-release must only run for tag refs')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profiling = root / 'build-profiling.yml'
        write_workflow(
            profiling,
            PROFILING_NEEDS.replace(
                "if: startsWith(github.ref, 'refs/tags/')",
                "if: github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')",
            ),
        )
        expect_fail(run(profiling), 'publish-release must only run for tag refs')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build = root / 'build.yml'
        write_workflow(build, '  build:\n    runs-on: ubuntu-latest\n')
        expect_fail(run(build), 'publish-release job not found')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        unknown = root / 'release-extra.yml'
        write_workflow(unknown, '  publish-release:\n    needs: build\n')
        expect_fail(run(unknown), 'publish-release has no required needs policy')

    print('Release needs guardrails validated')


if __name__ == '__main__':
    main()
