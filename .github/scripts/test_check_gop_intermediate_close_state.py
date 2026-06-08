#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gop_intermediate_close_state.py')

# Coverage probes used by the scan for GOP intermediate-close guardrails.
NORMALIZED_PROBES = (
    'GOP header write failure must finalize the header file before returning',
    'forbidden GOP intermediate close short-circuit regression: ',
    'missing GOP intermediate close guardrail: ',
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
                'source/output/gop.cpp': '\n'.join((
                    'int GOPOutput::writeHeaders(const x265_nal* p_nal, uint32_t nalcount)',
                    '{',
                    '    for(unsigned int i = 0; i < nalcount; i++)',
                    '    {',
                    '        if (!smart_fwrite(p_nal[i].payload, p_nal[i].sizeBytes, hdr_file))',
                    '        {',
                    '            bool closeFailed = std::ferror(hdr_file) != 0;',
                    '            if (std::fclose(hdr_file))',
                    '                closeFailed = true;',
                    '            if (closeFailed)',
                    '                b_fail = true;',
                    '            return -1;',
                    '        }',
                    '    }',
                    '    bool closeFailed = std::ferror(hdr_file) != 0;',
                    '}',
                    'int GOPOutput::writeFrame(const x265_nal* p_nalu, uint32_t nalcount, x265_picture& pic)',
                    '{',
                    '    if (is_keyframe) {',
                    '        if (data_file)',
                    '        {',
                    '            bool closeFailed = std::ferror(data_file) != 0;',
                    '            if (std::fclose(data_file))',
                    '                closeFailed = true;',
                    '            if (closeFailed)',
                    '            {',
                    '                b_fail = true;',
                    '                data_file = nullptr;',
                    '                return -1;',
                    '            }',
                    '            data_file = nullptr;',
                    '        }',
                    '        std::stringstream ss;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/gop.cpp': 'std::fclose(hdr_file);\n'})
        expect_fail(run_checker(root), 'missing GOP intermediate close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/gop.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(hdr_file) != 0;',
                    'if (std::fclose(hdr_file))',
                    '    closeFailed = true;',
                    '{',
                    '    b_fail = true;',
                    '    return -1;',
                    '}',
                    'bool closeFailed = std::ferror(data_file) != 0;',
                    'if (std::fclose(data_file))',
                    '    closeFailed = true;',
                    '{',
                    '    b_fail = true;',
                    '    data_file = nullptr;',
                    '    return -1;',
                    '}',
                    'data_file = nullptr;',
                    'if (std::ferror(data_file) || std::fclose(data_file))',
                    '    return -1;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden GOP intermediate close short-circuit regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/gop.cpp': '\n'.join((
                    'int GOPOutput::writeHeaders(const x265_nal* p_nal, uint32_t nalcount)',
                    '{',
                    '    for(unsigned int i = 0; i < nalcount; i++)',
                    '    {',
                    '        if (!smart_fwrite(p_nal[i].payload, p_nal[i].sizeBytes, hdr_file))',
                    '        {',
                    '            bool closeFailed = std::ferror(hdr_file) != 0;',
                    '            if (std::fclose(hdr_file))',
                    '                closeFailed = true;',
                    '            if (closeFailed)',
                    '                b_fail = true;',
                    '            return -1;',
                    '        }',
                    '    }',
                    '    bool closeFailed = std::ferror(hdr_file) != 0;',
                    '}',
                    'int GOPOutput::writeFrame(const x265_nal* p_nalu, uint32_t nalcount, x265_picture& pic)',
                    '{',
                    '    if (is_keyframe) {',
                    '        if (data_file)',
                    '        {',
                    '            bool closeFailed = std::ferror(data_file) != 0;',
                    '            if (std::fclose(data_file))',
                    '                closeFailed = true;',
                    '            data_file = nullptr;',
                    '            if (closeFailed)',
                    '            {',
                    '                b_fail = true;',
                    '                return -1;',
                    '            }',
                    '        }',
                    '        std::stringstream ss;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'GOP keyframe rollover must clear the prior data file before reopening the next GOP payload')

    print('GOP intermediate close-state guard tests passed')


if __name__ == '__main__':
    main()
