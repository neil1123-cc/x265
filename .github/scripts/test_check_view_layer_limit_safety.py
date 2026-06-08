#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_view_layer_limit_safety.py')

# Coverage probes used by the scan for view/layer limit guardrails.
NORMALIZED_PROBES = (
    'x265_check_params must derive and normalize numLayers after validating view/layer compatibility',
    'forbidden legacy CLI layer derivation: validate view/layer limits before assigning numLayers',
    'missing view/layer limit guardrail: ',
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
                    'static bool validateViewLayerLimits(x265_param* param, int& numLayers)',
                    '{',
                    '    if (param->numViews < 1 || param->numViews > MAX_VIEWS)',
                    '    {',
                    '        x265_log(param, X265_LOG_ERROR, "numViews must be between 1 and %d in this build\\n", MAX_VIEWS);',
                    '        return false;',
                    '    }',
                    '    if (param->numScalableLayers < 1 || param->numScalableLayers > MAX_SCALABLE_LAYERS)',
                    '    {',
                    '        x265_log(param, X265_LOG_ERROR, "numScalableLayers must be between 1 and %d in this build\\n", MAX_SCALABLE_LAYERS);',
                    '        return false;',
                    '    }',
                    '    if (param->numViews > 1 && param->numScalableLayers > 1)',
                    '    {',
                    '        x265_log(param, X265_LOG_ERROR, "alpha and multiview cannot be enabled together in this build\\n");',
                    '        return false;',
                    '    }',
                    '    numLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;',
                    '    if (numLayers < 1 || numLayers > MAX_LAYERS)',
                    '        return false;',
                    '    return true;',
                    '}',
                    'int derivedNumLayers = 0;',
                    'if (!validateViewLayerLimits(param, derivedNumLayers))',
                    '    return true;',
                    'param->numLayers = derivedNumLayers;',
                    'if (!outputfn)',
                    '    return true;',
                    'const int viewCount = param->format != 0 ? 1 : param->numViews;',
                )) + '\n',
                'source/common/param.cpp': '\n'.join((
                    'const int expectedNumLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;',
                    'CHECK(param->numScalableLayers < 1, "numScalableLayers must be at least 1");',
                    'CHECK(param->numViews < 1, "numViews must be at least 1");',
                    'CHECK(param->numViews > 1 && param->numScalableLayers > 1, "Alpha and Multi-View cannot be enabled together in this build");',
                    'CHECK(expectedNumLayers > MAX_LAYERS, "Derived layered encoding configuration exceeds this build");',
                    'param->numLayers = expectedNumLayers;',
                    'if (param->bEnableAlpha)',
                    '{',
                    '    CHECK(param->numScalableLayers != MAX_SCALABLE_LAYERS, "Alpha encoding requires exactly 2 scalable layers");',
                    '}',
                    'CHECK(param->numScalableLayers > 1 && !param->bEnableAlpha, "Multiple scalable layers require alpha encoding");',
                    'CHECK(param->format && param->numViews <= 1, "Multi-View input format requires more than one view");',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'param->numLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;\n',
                'source/common/param.cpp': 'param->numLayers = expectedNumLayers;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden legacy CLI layer derivation')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'static bool validateViewLayerLimits(x265_param* param, int& numLayers)',
                    '{',
                    '    if (param->numViews < 1 || param->numViews > MAX_VIEWS)',
                    '        return false;',
                    '    if (param->numScalableLayers < 1 || param->numScalableLayers > MAX_SCALABLE_LAYERS)',
                    '        return false;',
                    '    if (param->numViews > 1 && param->numScalableLayers > 1)',
                    '        return false;',
                    '    numLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;',
                    '    return true;',
                    '}',
                    'const int viewCount = param->format != 0 ? 1 : param->numViews;',
                    'int derivedNumLayers = 0;',
                    'if (!validateViewLayerLimits(param, derivedNumLayers))',
                    '    return true;',
                    'param->numLayers = derivedNumLayers;',
                )) + '\n',
                'source/common/param.cpp': '\n'.join((
                    'const int expectedNumLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;',
                    'CHECK(param->numScalableLayers < 1, "numScalableLayers must be at least 1");',
                    'CHECK(param->numViews < 1, "numViews must be at least 1");',
                    'CHECK(param->numViews > 1 && param->numScalableLayers > 1, "Alpha and Multi-View cannot be enabled together in this build");',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CLI parse must validate view/layer limits before using numViews or numLayers in fixed-array paths')

    print('View/layer limit safety tests passed')


if __name__ == '__main__':
    main()
