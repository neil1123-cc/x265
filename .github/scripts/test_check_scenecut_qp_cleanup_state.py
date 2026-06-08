#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scenecut_qp_cleanup_state.py')

# Coverage probes used by the scan for scenecut-QP cleanup guardrails.
NORMALIZED_PROBES = (
    'forbidden scenecut QP cleanup regression: ',
    'missing scenecut QP cleanup guardrail: ',
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
                'source/x265.cpp': '\n'.join((
                    'AbrEncoder* abrEnc = nullptr;',
                    'if (cliopt[0].scenecutAwareQpConfig)',
                    '{',
                    '    if (!cliopt[0].parseScenecutAwareQpConfig())',
                    '    {',
                    '        ret = 1;',
                    '        bool closeFailed = std::ferror(cliopt[0].scenecutAwareQpConfig) != 0;',
                    '        if (std::fclose(cliopt[0].scenecutAwareQpConfig))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            x265_log(nullptr, X265_LOG_WARNING, "Unable to close scenecut aware qp config file after parse failure\\n");',
                    '        cliopt[0].scenecutAwareQpConfig = nullptr;',
                    '    }',
                    '}',
                    'if (!ret)',
                    '    abrEnc = new AbrEncoder(cliopt, numEncodes, ret);',
                    'cleanup:',
                    'if (abrEnc)',
                    '    abrEnc->destroy();',
                    '    delete abrEnc;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265.cpp': 'std::fclose(cliopt[0].scenecutAwareQpConfig);\n'})
        expect_fail(run_checker(root), 'missing scenecut QP cleanup guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265.cpp': 'AbrEncoder* abrEnc = new AbrEncoder(cliopt, numEncodes, ret);\n'})
        expect_fail(run_checker(root), 'forbidden scenecut QP cleanup regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265.cpp': '\n'.join((
                    'AbrEncoder* abrEnc = nullptr;',
                    'if (cliopt[0].scenecutAwareQpConfig)',
                    '{',
                    '    if (!cliopt[0].parseScenecutAwareQpConfig())',
                    '    {',
                    '        ret = 1;',
                    '        cliopt[0].scenecutAwareQpConfig = nullptr;',
                    '        bool closeFailed = std::ferror(cliopt[0].scenecutAwareQpConfig) != 0;',
                    '        if (std::fclose(cliopt[0].scenecutAwareQpConfig))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            x265_log(nullptr, X265_LOG_WARNING, "Unable to close scenecut aware qp config file after parse failure\\n");',
                    '    }',
                    '}',
                    'if (!ret)',
                    '    abrEnc = new AbrEncoder(cliopt, numEncodes, ret);',
                    'cleanup:',
                    'if (abrEnc)',
                    '    abrEnc->destroy();',
                    '    delete abrEnc;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'scenecut QP parse failure must finalize and clear its config handle before the AbrEncoder creation gate')

    print('Scenecut QP cleanup guard tests passed')


if __name__ == '__main__':
    main()
