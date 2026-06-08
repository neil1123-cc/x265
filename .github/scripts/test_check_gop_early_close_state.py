#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_gop_early_close_state.py')

# Coverage probes used by the scan for GOP early-close guardrails.
NORMALIZED_PROBES = (
    'GOP setup failure must finalize the options file before returning',
    'GOP header setup failure must finalize the header file before returning',
    'forbidden GOP early-close short-circuit regression: ',
    'missing GOP early-close guardrail: ',
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
                    'void GOPOutput::setParam(x265_param *p_param)',
                    '{',
                    '    FILE* opt_file = open_file_for_write(dir_prefix + filename_prefix + ".options", false);',
                    '    if (std::fprintf(gop_file, "#options %s.options\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))',
                    '    {',
                    '        b_fail = true;',
                    '        bool closeFailed = std::ferror(opt_file) != 0;',
                    '        if (std::fclose(opt_file))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            b_fail = true;',
                    '        return;',
                    '    }',
                    '    std::fprintf(opt_file, "b-frames %d\\n",           p_param->bframes);',
                    '}',
                    'int GOPOutput::writeHeaders(const x265_nal* p_nal, uint32_t nalcount)',
                    '{',
                    '    if (std::fprintf(gop_file, "#headers %s.headers\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))',
                    '    {',
                    '        b_fail = true;',
                    '        bool closeFailed = std::ferror(hdr_file) != 0;',
                    '        if (std::fclose(hdr_file))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            b_fail = true;',
                    '        return -1;',
                    '    }',
                    '    for(unsigned int i = 0; i < nalcount; i++)',
                    '    {',
                    '    }',
                    '}',
                    'int GOPOutput::writeFrame(const x265_nal* p_nalu, uint32_t nalcount, x265_picture& pic)',
                    '{',
                    '    data_file = open_file_for_write(dir_prefix + data_filename, i_numframe > 0);',
                    '    if (std::fprintf(gop_file, "%s\\n", data_filename.c_str()) < 0 || std::fflush(gop_file))',
                    '    {',
                    '        b_fail = true;',
                    '        bool closeFailed = std::ferror(data_file) != 0;',
                    '        if (std::fclose(data_file))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            b_fail = true;',
                    '        data_file = nullptr;',
                    '        return -1;',
                    '    }',
                    '    else if (!data_file)',
                    '        return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/output/gop.cpp': 'std::fclose(hdr_file);\n'})
        expect_fail(run_checker(root), 'missing GOP early-close guardrail')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/gop.cpp': '\n'.join((
                    'bool closeFailed = std::ferror(opt_file) != 0;',
                    'if (std::fclose(opt_file))',
                    '    closeFailed = true;',
                    '    b_fail = true;',
                    'bool closeFailed = std::ferror(hdr_file) != 0;',
                    'if (std::fclose(hdr_file))',
                    '    closeFailed = true;',
                    '    b_fail = true;',
                    'bool closeFailed = std::ferror(data_file) != 0;',
                    'if (std::fclose(data_file))',
                    '    closeFailed = true;',
                    '    b_fail = true;',
                    'if (std::ferror(hdr_file) || std::fclose(hdr_file))',
                    '    b_fail = true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden GOP early-close short-circuit regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/output/gop.cpp': '\n'.join((
                    'void GOPOutput::setParam(x265_param *p_param)',
                    '{',
                    '    FILE* opt_file = open_file_for_write(dir_prefix + filename_prefix + ".options", false);',
                    '    if (std::fprintf(gop_file, "#options %s.options\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))',
                    '    {',
                    '        b_fail = true;',
                    '        bool closeFailed = std::ferror(opt_file) != 0;',
                    '        if (std::fclose(opt_file))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            b_fail = true;',
                    '        return;',
                    '    }',
                    '    std::fprintf(opt_file, "b-frames %d\\n",           p_param->bframes);',
                    '}',
                    'int GOPOutput::writeHeaders(const x265_nal* p_nal, uint32_t nalcount)',
                    '{',
                    '    if (std::fprintf(gop_file, "#headers %s.headers\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))',
                    '    {',
                    '        b_fail = true;',
                    '        bool closeFailed = std::ferror(hdr_file) != 0;',
                    '        if (std::fclose(hdr_file))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            b_fail = true;',
                    '        return -1;',
                    '    }',
                    '    for(unsigned int i = 0; i < nalcount; i++)',
                    '    {',
                    '    }',
                    '}',
                    'int GOPOutput::writeFrame(const x265_nal* p_nalu, uint32_t nalcount, x265_picture& pic)',
                    '{',
                    '    data_file = open_file_for_write(dir_prefix + data_filename, i_numframe > 0);',
                    '    if (std::fprintf(gop_file, "%s\\n", data_filename.c_str()) < 0 || std::fflush(gop_file))',
                    '    {',
                    '        b_fail = true;',
                    '        data_file = nullptr;',
                    '        bool closeFailed = std::ferror(data_file) != 0;',
                    '        if (std::fclose(data_file))',
                    '            closeFailed = true;',
                    '        if (closeFailed)',
                    '            b_fail = true;',
                    '        return -1;',
                    '    }',
                    '    else if (!data_file)',
                    '        return -1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'GOP data setup failure must finalize and clear the data file before returning')

    print('GOP early-close guard tests passed')


if __name__ == '__main__':
    main()
