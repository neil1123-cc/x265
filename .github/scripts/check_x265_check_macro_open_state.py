#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/common.h')
REQUIRED_SNIPPETS = (
    'FILE *fp = fopen("x265_check_failures.txt", "a");',
    'if (fp) { if (ferror(fp)) { bool closeFailed = ferror(fp) != 0; if (fclose(fp)) closeFailed = true; if (closeFailed) fprintf(stderr, "x265 [warning]: unable to close x265_check_failures.txt after open failure\\n"); } else { fprintf(fp, "%s:%d\\n", __FILE__, __LINE__); fprintf(fp, __VA_ARGS__); bool closeFailed = ferror(fp) != 0; if (fclose(fp)) closeFailed = true; if (closeFailed) fprintf(stderr, "x265 [warning]: unable to finalize x265_check_failures.txt\\n"); } }',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing x265 check macro open-state guardrail: {snippet}'))

    open_pos = text.find('FILE *fp = fopen("x265_check_failures.txt", "a");')
    ferror_pos = text.find('if (fp) { if (ferror(fp)) {', open_pos)
    write_pos = text.find('else { fprintf(fp, "%s:%d\\n", __FILE__, __LINE__);', ferror_pos)
    if -1 in (open_pos, ferror_pos, write_pos) or not (open_pos < ferror_pos < write_pos):
        failures.append((TARGET.as_posix(), 0, 'X265_CHECK must reject open-state errors before writing the failure log'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265 check macro open state')
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

    print('x265 check macro open-state guard validated')


if __name__ == '__main__':
    main()
