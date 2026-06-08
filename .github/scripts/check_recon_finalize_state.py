#!/usr/bin/env python3
import argparse
from pathlib import Path


REQUIRED = {
    'source/output/output.h': (
        'virtual bool finalize() = 0;',
    ),
    'source/output/yuv.h': (
        'bool finalized;',
        'bool finalize();',
    ),
    'source/output/y4m.h': (
        'bool finalized;',
        'bool finalize();',
    ),
    'source/output/yuv.cpp': (
        'finalized(false)',
        'finalize();',
        'bool YUVOutput::finalize()',
        'if (finalized)',
        'return !failed;',
        'failed |= std::ferror(ofs) != 0;',
        'failed |= std::fflush(ofs) != 0;',
        'failed |= std::fclose(ofs) != 0;',
        'ofs = nullptr;',
    ),
    'source/output/y4m.cpp': (
        'finalized(false)',
        'finalize();',
        'bool Y4MOutput::finalize()',
        'if (finalized)',
        'return !failed;',
        'failed |= std::ferror(ofs) != 0;',
        'failed |= std::fflush(ofs) != 0;',
        'failed |= std::fclose(ofs) != 0;',
        'ofs = nullptr;',
    ),
    'source/x265cli.h': (
        'bool destroy();',
    ),
    'source/x265cli.cpp': (
        'closeFailed |= !recon[i]->finalize();',
        'return closeFailed;',
    ),
    'source/x265.cpp': (
        'bool destroyFailed = false;',
        'destroyFailed |= cliopt[idx].destroy();',
        'if (!ret && destroyFailed)',
        'ret = 3;',
    ),
}


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    for relative, snippets in REQUIRED.items():
        path = repo_root / relative
        if not path.is_file():
            failures.append((relative, 0, 'missing file'))
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        for snippet in snippets:
            if snippet not in text:
                failures.append((relative, 0, f'missing recon finalize-state guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check recon finalize state')
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

    print('Recon finalize-state guard validated')


if __name__ == '__main__':
    main()
