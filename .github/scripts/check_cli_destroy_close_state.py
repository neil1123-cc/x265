#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
FORBIDDEN_SNIPPETS = (
    'closeFailed |= std::ferror(qpfile) || std::fclose(qpfile);',
    'closeFailed |= std::ferror(zoneFile) || std::fclose(zoneFile);',
    'closeFailed |= std::ferror(dolbyVisionRpu) || std::fclose(dolbyVisionRpu);',
    'closeFailed |= std::ferror(scenecutAwareQpConfig) || std::fclose(scenecutAwareQpConfig);',
    'closeFailed |= std::ferror(multiViewConfig) || std::fclose(multiViewConfig);',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = false;',
    'bool fileCloseFailed = std::ferror(qpfile) != 0;',
    'if (std::fclose(qpfile))',
    'closeFailed |= fileCloseFailed;',
    'bool fileCloseFailed = std::ferror(zoneFile) != 0;',
    'if (std::fclose(zoneFile))',
    'bool fileCloseFailed = std::ferror(dolbyVisionRpu) != 0;',
    'if (std::fclose(dolbyVisionRpu))',
    'bool fileCloseFailed = std::ferror(scenecutAwareQpConfig) != 0;',
    'if (std::fclose(scenecutAwareQpConfig))',
    'scenecutAwareQpConfig = nullptr;',
    'bool fileCloseFailed = std::ferror(multiViewConfig) != 0;',
    'if (std::fclose(multiViewConfig))',
    'multiViewConfig = nullptr;',
    'output->closeFile(0, 0);',
    'output->release();',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "CLI file handle cleanup reported a close failure\\n");',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden CLI destroy short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing CLI destroy close-state guardrail: {snippet}'))

    output_close_pos = text.find('output->closeFile(0, 0);')
    output_release_pos = text.find('output->release();', output_close_pos if output_close_pos >= 0 else 0)
    if -1 in (output_close_pos, output_release_pos) or not (output_close_pos < output_release_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI destroy must close output handles before releasing the output wrapper'))

    warn_pos = text.find('if (closeFailed)')
    log_pos = text.find('x265_log(param, X265_LOG_WARNING, "CLI file handle cleanup reported a close failure\\n");', warn_pos if warn_pos >= 0 else 0)
    free_pos = text.find('api->param_free(param);', log_pos if log_pos >= 0 else 0)
    null_pos = text.find('param = nullptr;', free_pos if free_pos >= 0 else 0)
    if -1 in (warn_pos, log_pos, free_pos, null_pos) or not (warn_pos < log_pos < free_pos < null_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI destroy must report close failures before freeing param context'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI destroy close state')
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

    print('CLI destroy close-state guard validated')


if __name__ == '__main__':
    main()
