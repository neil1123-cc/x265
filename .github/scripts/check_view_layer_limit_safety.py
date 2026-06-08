#!/usr/bin/env python3
import argparse
from pathlib import Path


CLI_TARGET = Path('source/x265cli.cpp')
PARAM_TARGET = Path('source/common/param.cpp')

REQUIRED_CLI_SNIPPETS = (
    'static bool validateViewLayerLimits(x265_param* param, int& numLayers)',
    'if (param->numViews < 1 || param->numViews > MAX_VIEWS)',
    '"numViews must be between 1 and %d in this build\\n", MAX_VIEWS',
    'if (param->numScalableLayers < 1 || param->numScalableLayers > MAX_SCALABLE_LAYERS)',
    '"numScalableLayers must be between 1 and %d in this build\\n", MAX_SCALABLE_LAYERS',
    'if (param->numViews > 1 && param->numScalableLayers > 1)',
    '"alpha and multiview cannot be enabled together in this build\\n"',
    'numLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;',
    'if (!validateViewLayerLimits(param, derivedNumLayers))',
    'param->numLayers = derivedNumLayers;',
    'const int viewCount = param->format != 0 ? 1 : param->numViews;',
)

FORBIDDEN_CLI_SNIPPETS = (
    'param->numLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;',
)

REQUIRED_PARAM_SNIPPETS = (
    'const int expectedNumLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;',
    'CHECK(param->numScalableLayers < 1, "numScalableLayers must be at least 1");',
    'CHECK(param->numViews < 1, "numViews must be at least 1");',
    'CHECK(param->numViews > 1 && param->numScalableLayers > 1, "Alpha and Multi-View cannot be enabled together in this build");',
    'CHECK(expectedNumLayers > MAX_LAYERS, "Derived layered encoding configuration exceeds this build");',
    'param->numLayers = expectedNumLayers;',
    'CHECK(param->numScalableLayers != MAX_SCALABLE_LAYERS, "Alpha encoding requires exactly 2 scalable layers");',
    'CHECK(param->numScalableLayers > 1 && !param->bEnableAlpha, "Multiple scalable layers require alpha encoding");',
    'CHECK(param->format && param->numViews <= 1, "Multi-View input format requires more than one view");',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    cli_path = repo_root / CLI_TARGET
    param_path = repo_root / PARAM_TARGET
    for path in (cli_path, param_path):
        if not path.is_file():
            return [(path.relative_to(repo_root).as_posix(), 0, 'missing file')]

    cli_text = cli_path.read_text(encoding='utf-8', errors='ignore')
    param_text = param_path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    for snippet in FORBIDDEN_CLI_SNIPPETS:
        if snippet in cli_text:
            failures.append((CLI_TARGET.as_posix(), 0, 'forbidden legacy CLI layer derivation: validate view/layer limits before assigning numLayers'))
            return failures

    for snippet in REQUIRED_CLI_SNIPPETS:
        if snippet not in cli_text:
            failures.append((CLI_TARGET.as_posix(), 0, f'missing view/layer limit guardrail: {snippet}'))
    for snippet in REQUIRED_PARAM_SNIPPETS:
        if snippet not in param_text:
            failures.append((PARAM_TARGET.as_posix(), 0, f'missing view/layer limit guardrail: {snippet}'))

    helper_pos = cli_text.find('static bool validateViewLayerLimits(x265_param* param, int& numLayers)')
    call_pos = cli_text.find('if (!validateViewLayerLimits(param, derivedNumLayers))')
    assign_pos = cli_text.find('param->numLayers = derivedNumLayers;', call_pos if call_pos != -1 else 0)
    view_count_pos = cli_text.find('const int viewCount = param->format != 0 ? 1 : param->numViews;', assign_pos if assign_pos != -1 else 0)
    if -1 in (helper_pos, call_pos, assign_pos, view_count_pos) or not (helper_pos < call_pos < assign_pos < view_count_pos):
        failures.append((CLI_TARGET.as_posix(), 0, 'CLI parse must validate view/layer limits before using numViews or numLayers in fixed-array paths'))

    expected_pos = param_text.find('const int expectedNumLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;')
    combo_pos = param_text.find('CHECK(param->numViews > 1 && param->numScalableLayers > 1, "Alpha and Multi-View cannot be enabled together in this build");')
    normalize_pos = param_text.find('param->numLayers = expectedNumLayers;', combo_pos if combo_pos != -1 else 0)
    if -1 in (expected_pos, combo_pos, normalize_pos) or not (expected_pos < combo_pos < normalize_pos):
        failures.append((PARAM_TARGET.as_posix(), 0, 'x265_check_params must derive and normalize numLayers after validating view/layer compatibility'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check view/layer limit safety guardrails')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('View/layer limit safety validated')


if __name__ == '__main__':
    main()
