#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_preset_index_parse_usage.py')

# Coverage probes used by the scan for preset-index parse guardrails.
NORMALIZED_PROBES = (
    'expected preset index parse helper to be used in both preset entry points',
    'forbidden preset index parse regression: ',
    'missing preset index parse guardrail: ',
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
                'source/common/param.cpp': '\n'.join((
                    'static const char* parsePresetIndexName(const char* preset)',
                    'int index = parseOptionIntToken(preset, std::strlen(preset), bPresetIndexError);',
                    'if (!bPresetIndexError && index >= 0 && index < (int)(sizeof(x265_preset_names) / sizeof(*x265_preset_names) - 1))',
                    'preset = parsePresetIndexName(preset);',
                    'preset = parsePresetIndexName(preset);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': 'int i = strtol(preset, &end, 10);\n'})
        expect_fail(run_checker(root), 'forbidden preset index parse regression')

    print('Preset index parse guard tests passed')


if __name__ == '__main__':
    main()
