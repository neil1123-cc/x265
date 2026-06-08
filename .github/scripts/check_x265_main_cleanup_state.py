#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265.cpp')
FORBIDDEN_SNIPPETS = (
    'if (isAbrLadder && !abrConfig)\n        std::exit(1);',
    'x265_log(nullptr, X265_LOG_ERROR, "ABR ladder config contains no valid encode entries\\n");\n            std::exit(1);',
    'if (!parseAbrConfig(abrConfig, cliopt, numEncodes))\n            std::exit(1);',
    'if (!setRefContext(cliopt, numEncodes))\n            std::exit(1);',
    'cliopt[0].destroy();\n        std::exit(1);',
    'std::ferror(abrConfig) || std::fclose(abrConfig)',
    'std::ferror(cliopt[0].scenecutAwareQpConfig) || std::fclose(cliopt[0].scenecutAwareQpConfig)',
)
REQUIRED_SNIPPETS = (
    'int ret = 0;',
    'CLIOptions* cliopt = nullptr;',
    'AbrEncoder* abrEnc = nullptr;',
    'ret = 1;',
    'else if (cliopt[0].parseExitCode >= 0)',
    'ret = cliopt[0].parseExitCode;',
    'goto cleanup;',
    'cleanup:',
    'if (abrConfig)',
    'bool closeFailed = std::ferror(abrConfig) != 0;',
    'if (std::fclose(abrConfig))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file during main cleanup\\n");',
    'abrConfig = nullptr;',
    'if (abrEnc)',
    'abrEnc->destroy();',
    'delete abrEnc;',
    'bool destroyFailed = false;',
    'if (cliopt)',
    'destroyFailed |= cliopt[idx].destroy();',
    'if (!ret && destroyFailed)',
    'ret = 3;',
    'delete[] cliopt;',
)
REGION_START = 'int main(int argc, char **argv)'
REGION_END = 'return ret;'


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
    if -1 not in (region_start, region_end):
        region_end += len(REGION_END)
        region = text[region_start:region_end]
    else:
        region = text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden x265 main cleanup regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing x265 main cleanup guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'cleanup:',
                'if (abrConfig)',
                'bool closeFailed = std::ferror(abrConfig) != 0;',
                'if (std::fclose(abrConfig))',
                'closeFailed = true;',
                'if (closeFailed)',
                'x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file during main cleanup\\n");',
                'abrConfig = nullptr;',
                'if (abrEnc)',
                'abrEnc->destroy();',
                'delete abrEnc;',
                'bool destroyFailed = false;',
                'if (cliopt)',
                'destroyFailed |= cliopt[idx].destroy();',
                'if (!ret && destroyFailed)',
                'ret = 3;',
                'delete[] cliopt;',
                'return ret;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'x265 main cleanup must finalize abrConfig before tearing down the encoder and CLI options'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265 main cleanup state')
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

    print('x265 main cleanup guard validated')


if __name__ == '__main__':
    main()
