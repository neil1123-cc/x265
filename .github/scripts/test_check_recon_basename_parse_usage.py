#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_recon_basename_parse_usage.py')

# Coverage probes used by the scan for recon basename parse guardrails.
NORMALIZED_PROBES = (
    'forbidden recon basename parse regression: ',
    'missing recon basename parse guardrail: ',
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
                    'std::vector<std::string> derivedReconNames;',
                    'if (param->bEnableAlpha || param->numViews > 1)',
                    'std::string temp = reconfn[0];',
                    "size_t extensionPos = temp.find_last_of('.');",
                    'if (extensionPos == 0)',
                    'x265_log(param, X265_LOG_ERROR, "recon file name must include a non-empty base name for alpha or multiview output\\n");',
                    'if (extensionPos != std::string::npos)',
                    'temp.erase(extensionPos);',
                    'if (temp.empty())',
                    'derivedReconNames.reserve(param->numLayers);',
                    'derivedReconNames.push_back(temp + "-" + std::to_string(view) + ".yuv");',
                    'reconfn[view] = derivedReconNames.back().c_str();',
                    'for (int i = 0; i < param->numLayers; i++)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265cli.cpp': 'char* temp = new char[reconNameLen + 1];\n'})
        expect_fail(run_checker(root), 'forbidden recon basename parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'std::vector<std::string> derivedReconNames;',
                    'if (param->bEnableAlpha || param->numViews > 1)',
                    'std::string temp = reconfn[0];',
                    "size_t extensionPos = temp.find_last_of('.');",
                    'if (extensionPos == 0)',
                    'x265_log(param, X265_LOG_ERROR, "recon file name must include a non-empty base name for alpha or multiview output\\n");',
                    'if (extensionPos != std::string::npos)',
                    'temp.erase(extensionPos);',
                    'derivedReconNames.reserve(param->numLayers);',
                    'derivedReconNames.push_back(temp + "-" + std::to_string(view) + ".yuv");',
                    'reconfn[view] = derivedReconNames.back().c_str();',
                    'if (temp.empty())',
                    'for (int i = 0; i < param->numLayers; i++)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Recon basename derivation must validate the base filename before erasing the extension and publishing per-layer recon names')

    print('Recon basename parse guard tests passed')


if __name__ == '__main__':
    main()
