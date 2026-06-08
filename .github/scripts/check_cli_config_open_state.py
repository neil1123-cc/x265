#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(this->qpfile) || std::fclose(this->qpfile)',
    'std::ferror(this->dolbyVisionRpu) || std::fclose(this->dolbyVisionRpu)',
    'std::ferror(this->scenecutAwareQpConfig) || std::fclose(this->scenecutAwareQpConfig)',
    'std::ferror(this->multiViewConfig) || std::fclose(this->multiViewConfig)',
    'std::ferror(this->zoneFile) || std::fclose(this->zoneFile)',
)
REQUIRED_SNIPPETS = (
    'this->qpfile = x265_fopen(optarg, "rb");',
    'if (!this->qpfile)',
    'else if (std::ferror(this->qpfile))',
    'bool closeFailed = std::ferror(this->qpfile) != 0;',
    'if (std::fclose(this->qpfile))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "Unable to close qpfile after open failure\\n");',
    'this->qpfile = nullptr;',
    'this->dolbyVisionRpu = x265_fopen(optarg, "rb");',
    'else if (std::ferror(this->dolbyVisionRpu))',
    'bool closeFailed = std::ferror(this->dolbyVisionRpu) != 0;',
    'if (std::fclose(this->dolbyVisionRpu))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "Unable to close Dolby Vision RPU metadata file after open failure\\n");',
    'this->dolbyVisionRpu = nullptr;',
    'this->scenecutAwareQpConfig = x265_fopen(optarg, "rb");',
    'if (!this->scenecutAwareQpConfig)',
    'else if (std::ferror(this->scenecutAwareQpConfig))',
    'bool closeFailed = std::ferror(this->scenecutAwareQpConfig) != 0;',
    'if (std::fclose(this->scenecutAwareQpConfig))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "Unable to close scenecut aware qp config file after open failure\\n");',
    'this->scenecutAwareQpConfig = nullptr;',
    'this->multiViewConfig = x265_fopen(optarg, "rb");',
    'if (!this->multiViewConfig)',
    'else if (std::ferror(this->multiViewConfig))',
    'bool closeFailed = std::ferror(this->multiViewConfig) != 0;',
    'if (std::fclose(this->multiViewConfig))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "Unable to close multiview config file after open failure\\n");',
    'this->multiViewConfig = nullptr;',
    'this->zoneFile = x265_fopen(optarg, "rb");',
    'if (!this->zoneFile)',
    'else if (std::ferror(this->zoneFile))',
    'bool closeFailed = std::ferror(this->zoneFile) != 0;',
    'if (std::fclose(this->zoneFile))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "Unable to close zone file after open failure\\n");',
    'this->zoneFile = nullptr;',
)

FAIL_FAST_OPEN_FAILURES = (
    (
        'qpfile',
        'this->qpfile = x265_fopen(optarg, "rb");',
        'if (!this->qpfile)',
        'x265_log_file(param, X265_LOG_ERROR, "%s qpfile not found or error in opening qp file\\n", optarg);',
        'return true;',
    ),
    (
        'scenecut aware qp config',
        'this->scenecutAwareQpConfig = x265_fopen(optarg, "rb");',
        'if (!this->scenecutAwareQpConfig)',
        'x265_log_file(param, X265_LOG_ERROR, "%s scenecut aware qp config file not found or error in opening config file\\n", optarg);',
        'return true;',
    ),
    (
        'multiview config',
        'this->multiViewConfig = x265_fopen(optarg, "rb");',
        'if (!this->multiViewConfig)',
        'x265_log_file(param, X265_LOG_ERROR, "%s Multiview config file not found or error in opening config file\\n", optarg);',
        'return true;',
    ),
    (
        'zone file',
        'this->zoneFile = x265_fopen(optarg, "rb");',
        'if (!this->zoneFile)',
        'x265_log_file(param, X265_LOG_ERROR, "%s zone file not found or error in opening zone file\\n", optarg);',
        'return true;',
    ),
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
            failures.append((TARGET.as_posix(), 0, f'forbidden cli config open-state short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing cli config open-state guardrail: {snippet}'))

    for label, open_snippet, branch_snippet, log_snippet, return_snippet in FAIL_FAST_OPEN_FAILURES:
        open_pos = text.find(open_snippet)
        branch_pos = text.find(branch_snippet, open_pos if open_pos >= 0 else 0)
        log_pos = text.find(log_snippet, branch_pos if branch_pos >= 0 else 0)
        return_pos = text.find(return_snippet, log_pos if log_pos >= 0 else 0)
        ferror_pos = text.find('else if', branch_pos if branch_pos >= 0 else 0)
        if -1 in (open_pos, branch_pos, log_pos, return_pos, ferror_pos) or not (open_pos < branch_pos < log_pos < return_pos < ferror_pos):
            failures.append((TARGET.as_posix(), 0, f'{label} open failure must log and return true before further parsing'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI config open state')
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

    print('CLI config open-state guard validated')


if __name__ == '__main__':
    main()
