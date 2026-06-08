#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cli_config_open_state.py')


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
                    'this->qpfile = x265_fopen(optarg, "rb");',
                    'if (!this->qpfile)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s qpfile not found or error in opening qp file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(this->qpfile))',
                    'bool closeFailed = std::ferror(this->qpfile) != 0;',
                    'if (std::fclose(this->qpfile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close qpfile after open failure\\n");',
                    'this->qpfile = nullptr;',
                    'this->dolbyVisionRpu = x265_fopen(optarg, "rb");',
                    'else if (std::ferror(this->dolbyVisionRpu))',
                    'bool closeFailed = std::ferror(this->dolbyVisionRpu) != 0;',
                    'if (std::fclose(this->dolbyVisionRpu))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close Dolby Vision RPU metadata file after open failure\\n");',
                    'this->dolbyVisionRpu = nullptr;',
                    'this->scenecutAwareQpConfig = x265_fopen(optarg, "rb");',
                    'if (!this->scenecutAwareQpConfig)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s scenecut aware qp config file not found or error in opening config file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(this->scenecutAwareQpConfig))',
                    'bool closeFailed = std::ferror(this->scenecutAwareQpConfig) != 0;',
                    'if (std::fclose(this->scenecutAwareQpConfig))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close scenecut aware qp config file after open failure\\n");',
                    'this->scenecutAwareQpConfig = nullptr;',
                    'this->multiViewConfig = x265_fopen(optarg, "rb");',
                    'if (!this->multiViewConfig)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s Multiview config file not found or error in opening config file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(this->multiViewConfig))',
                    'bool closeFailed = std::ferror(this->multiViewConfig) != 0;',
                    'if (std::fclose(this->multiViewConfig))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close multiview config file after open failure\\n");',
                    'this->multiViewConfig = nullptr;',
                    'this->zoneFile = x265_fopen(optarg, "rb");',
                    'if (!this->zoneFile)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s zone file not found or error in opening zone file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(this->zoneFile))',
                    'bool closeFailed = std::ferror(this->zoneFile) != 0;',
                    'if (std::fclose(this->zoneFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close zone file after open failure\\n");',
                    'this->zoneFile = nullptr;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'this->qpfile = x265_fopen(optarg, "rb");\nif (!this->qpfile)\n    return true;\n',
            },
        )
        expect_fail(run_checker(root), 'missing cli config open-state guardrail: else if (std::ferror(this->qpfile))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'this->qpfile = x265_fopen(optarg, "rb");',
                    'if (!this->qpfile)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s qpfile not found or error in opening qp file\\n", optarg);',
                    'else if (std::ferror(this->qpfile))',
                    '    return true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'qpfile open failure must log and return true before further parsing')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'this->qpfile = x265_fopen(optarg, "rb");',
                    'if (!this->qpfile)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s qpfile not found or error in opening qp file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(this->qpfile))',
                    'bool closeFailed = std::ferror(this->qpfile) != 0;',
                    'if (std::fclose(this->qpfile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close qpfile after open failure\\n");',
                    'this->qpfile = nullptr;',
                    'if (std::ferror(this->qpfile) || std::fclose(this->qpfile))',
                    '    return true;',
                    'this->dolbyVisionRpu = x265_fopen(optarg, "rb");',
                    'else if (std::ferror(this->dolbyVisionRpu))',
                    'bool closeFailed = std::ferror(this->dolbyVisionRpu) != 0;',
                    'if (std::fclose(this->dolbyVisionRpu))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close Dolby Vision RPU metadata file after open failure\\n");',
                    'this->dolbyVisionRpu = nullptr;',
                    'this->scenecutAwareQpConfig = x265_fopen(optarg, "rb");',
                    'if (!this->scenecutAwareQpConfig)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s scenecut aware qp config file not found or error in opening config file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(this->scenecutAwareQpConfig))',
                    'bool closeFailed = std::ferror(this->scenecutAwareQpConfig) != 0;',
                    'if (std::fclose(this->scenecutAwareQpConfig))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close scenecut aware qp config file after open failure\\n");',
                    'this->scenecutAwareQpConfig = nullptr;',
                    'this->multiViewConfig = x265_fopen(optarg, "rb");',
                    'if (!this->multiViewConfig)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s Multiview config file not found or error in opening config file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(this->multiViewConfig))',
                    'bool closeFailed = std::ferror(this->multiViewConfig) != 0;',
                    'if (std::fclose(this->multiViewConfig))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close multiview config file after open failure\\n");',
                    'this->multiViewConfig = nullptr;',
                    'this->zoneFile = x265_fopen(optarg, "rb");',
                    'if (!this->zoneFile)',
                    '    x265_log_file(param, X265_LOG_ERROR, "%s zone file not found or error in opening zone file\\n", optarg);',
                    '    return true;',
                    'else if (std::ferror(this->zoneFile))',
                    'bool closeFailed = std::ferror(this->zoneFile) != 0;',
                    'if (std::fclose(this->zoneFile))',
                    '    closeFailed = true;',
                    'if (closeFailed)',
                    '    x265_log(param, X265_LOG_WARNING, "Unable to close zone file after open failure\\n");',
                    'this->zoneFile = nullptr;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden cli config open-state short-circuit close regression: std::ferror(this->qpfile) || std::fclose(this->qpfile)')

    print('CLI config open-state guard tests passed')


if __name__ == '__main__':
    main()
