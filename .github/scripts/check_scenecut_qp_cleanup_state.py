#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265.cpp')
FORBIDDEN_SNIPPETS = (
    'AbrEncoder* abrEnc = new AbrEncoder(cliopt, numEncodes, ret);',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = std::ferror(cliopt[0].scenecutAwareQpConfig) != 0;',
    'if (std::fclose(cliopt[0].scenecutAwareQpConfig))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(nullptr, X265_LOG_WARNING, "Unable to close scenecut aware qp config file after parse failure\\n");',
    'cliopt[0].scenecutAwareQpConfig = nullptr;',
    'ret = 1;',
    'AbrEncoder* abrEnc = nullptr;',
    'if (!ret)',
    'abrEnc = new AbrEncoder(cliopt, numEncodes, ret);',
    'if (abrEnc)',
    'abrEnc->destroy();',
    'delete abrEnc;',
)
REGION_START = 'AbrEncoder* abrEnc = nullptr;'
REGION_END = 'delete[] cliopt;'


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find(REGION_START)
    region_end = text.find(REGION_END, region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden scenecut QP cleanup regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing scenecut QP cleanup guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'AbrEncoder* abrEnc = nullptr;',
                'if (!cliopt[0].parseScenecutAwareQpConfig())',
                'ret = 1;',
                'bool closeFailed = std::ferror(cliopt[0].scenecutAwareQpConfig) != 0;',
                'if (std::fclose(cliopt[0].scenecutAwareQpConfig))',
                'closeFailed = true;',
                'if (closeFailed)',
                'x265_log(nullptr, X265_LOG_WARNING, "Unable to close scenecut aware qp config file after parse failure\\n");',
                'cliopt[0].scenecutAwareQpConfig = nullptr;',
                'if (!ret)',
                'abrEnc = new AbrEncoder(cliopt, numEncodes, ret);',
                'cleanup:',
                'if (abrEnc)',
                'abrEnc->destroy();',
                'delete abrEnc;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'scenecut QP parse failure must finalize and clear its config handle before the AbrEncoder creation gate'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scenecut QP cleanup state')
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

    print('Scenecut QP cleanup guard validated')


if __name__ == '__main__':
    main()
