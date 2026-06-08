#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_csvlog_api_null_guards.py')

# Normalized checker probes used by the coverage scan for label-formatted failures.
NORMALIZED_PROBES = (
    'missing  function',
    'missing  null guardrail: ',
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


def valid_text():
    return '\n'.join((
        'FILE* x265_csvlog_open(const x265_param* param)',
        '{',
        '    if (!param)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_open requires a non-null parameter struct\\n");',
        '        return nullptr;',
        '    }',
        '    FILE *csvfp = x265_fopen(param->csvfn, "r");',
        '}',
        'void x265_csvlog_frame(const x265_param* param, const x265_picture* pic)',
        '{',
        '    if (!param || !pic)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_frame requires non-null param and picture\\n");',
        '        return;',
        '    }',
        '    if (!param->csvfpt)',
        '        return;',
        '    const x265_frame_stats* frameStats = &pic->frameData;',
        '}',
        'void x265_csvlog_encode(const x265_param *p, const x265_stats *stats, int padx, int pady, int argc, char** argv)',
        '{',
        '    if (!p || !stats)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_encode requires non-null param and stats\\n");',
        '        return;',
        '    }',
        '    if (!p->csvfpt)',
        '        return;',
        '    const x265_api * api = x265_api_get(0);',
        '    if (!api)',
        '        return;',
        '    if (argc > 0 && argv)',
        '    {',
        '        fputs(argv[i], p->csvfpt);',
        '    }',
        '    fprintf(p->csvfpt, "%.2f,", stats->elapsedEncodeTime);',
        '    fprintf(p->csvfpt, " %s\\n", api->version_str);',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': ''})
        expect_fail(run_checker(root), 'missing x265_csvlog_open function')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!param)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_open requires a non-null parameter struct\\n");\n'
                    '        return nullptr;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_csvlog_open null guardrail: if (!param)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (!param || !pic)\n'
                    '    {\n'
                    '        x265_log(nullptr, X265_LOG_ERROR, "x265_csvlog_frame requires non-null param and picture\\n");\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_csvlog_frame null guardrail: if (!param || !pic)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': valid_text().replace(
                    '    if (argc > 0 && argv)\n',
                    '    if (argc)\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing x265_csvlog_encode null guardrail: if (argc > 0 && argv)')

    print('CSV log API null guard tests passed')


if __name__ == '__main__':
    main()
