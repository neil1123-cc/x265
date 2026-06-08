#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_output_fail_state.py')

# Coverage probe used by the scan for the reviewed analysis output fail-state guardrail.
NORMALIZED_PROBES = (
    'missing analysis output fail-state guardrail in writeAnalysisFileRefine: ',
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


WRITE_BLOCK = '\n'.join((
    'void Encoder::writeAnalysisFile(x265_analysis_data* analysis, FrameData &curEncData)',
    '{',
    '    auto failAnalysisWrite = [this]()',
    '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "Error writing analysis data\\n");',
    '        if (m_analysisFileOut)',
    '        {',
    '            if (std::fclose(m_analysisFileOut))',
    '                closeFailed = true;',
    '            x265_log_file(m_param, X265_LOG_WARNING, "failed to close analysis output file \\"%s\\" after write failure\\n", m_param->analysisSave);',
    '            m_analysisFileOut = nullptr;',
    '        }',
    '        m_aborted = true;',
    '    };',
    '    if (m_aborted)',
    '        return;',
    '    if (!m_analysisFileOut)',
    '    {',
    '        m_aborted = true;',
    '        return;',
    '    }',
    '}',
))
REFINE_BLOCK = '\n'.join((
    'void Encoder::writeAnalysisFileRefine(x265_analysis_data* analysis, FrameData &curEncData)',
    '{',
    '    auto failAnalysisWrite = [this]()',
    '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "Error writing analysis 2 pass data\\n");',
    '        if (m_analysisFileOut)',
    '        {',
    '            if (std::fclose(m_analysisFileOut))',
    '                closeFailed = true;',
    '            x265_log_file(m_param, X265_LOG_WARNING, "failed to close analysis output file \\"%s\\" after refine write failure\\n", m_param->analysisSave);',
    '            m_analysisFileOut = nullptr;',
    '        }',
    '        m_aborted = true;',
    '    };',
    '    if (m_aborted)',
    '        return;',
    '    if (!m_analysisFileOut)',
    '    {',
    '        m_aborted = true;',
    '        return;',
    '    }',
    '}',
))
PRINT_BLOCK = '\n'.join((
    'void Encoder::printReconfigureParams()',
    '{',
    '}',
))
PASS_SOURCE = '\n'.join((WRITE_BLOCK, REFINE_BLOCK, PRINT_BLOCK)) + '\n'


def join_blocks(*blocks):
    return '\n'.join(blocks) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': join_blocks(
                    WRITE_BLOCK.replace('            m_analysisFileOut = nullptr;\n', '', 1),
                    REFINE_BLOCK,
                    PRINT_BLOCK,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing analysis output fail-state guardrail in writeAnalysisFile: m_analysisFileOut = nullptr;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': join_blocks(
                    WRITE_BLOCK.replace(
                        '        m_aborted = true;\n',
                        '        x265_free_analysis_data(m_param, analysis);\n        m_aborted = true;\n',
                        1,
                    ),
                    REFINE_BLOCK,
                    PRINT_BLOCK,
                ),
            },
        )
        expect_fail(run_checker(root), 'writeAnalysisFile must leave analysis-data cleanup to the caller after write failure')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': join_blocks(REFINE_BLOCK, PRINT_BLOCK)})
        expect_fail(run_checker(root), 'missing analysis output fail-state guardrail: writeAnalysisFile block')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': join_blocks(WRITE_BLOCK, PRINT_BLOCK)})
        expect_fail(run_checker(root), 'missing analysis output fail-state guardrail: writeAnalysisFileRefine block')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': join_blocks(
                    WRITE_BLOCK.replace(
                        '            m_analysisFileOut = nullptr;\n'
                        '        }\n'
                        '        m_aborted = true;\n'
                        '    };\n'
                        '    if (m_aborted)\n'
                        '        return;\n',
                        '        }\n'
                        '        m_aborted = true;\n'
                        '    };\n'
                        '    if (m_aborted)\n'
                        '        return;\n'
                        '    m_analysisFileOut = nullptr;\n',
                        1,
                    ),
                    REFINE_BLOCK,
                    PRINT_BLOCK,
                ),
            },
        )
        expect_fail(run_checker(root), 'writeAnalysisFile must retire the failed stream before later aborted/null stream guards')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': join_blocks(
                    WRITE_BLOCK,
                    REFINE_BLOCK.replace(
                        '        m_aborted = true;\n',
                        '        x265_free_analysis_data(m_param, analysis);\n        m_aborted = true;\n',
                        1,
                    ),
                    PRINT_BLOCK,
                ),
            },
        )
        expect_fail(run_checker(root), 'writeAnalysisFileRefine must leave analysis-data cleanup to the caller after write failure')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': join_blocks(
                    WRITE_BLOCK,
                    REFINE_BLOCK.replace(
                        '            m_analysisFileOut = nullptr;\n'
                        '        }\n'
                        '        m_aborted = true;\n'
                        '    };\n'
                        '    if (m_aborted)\n'
                        '        return;\n',
                        '        }\n'
                        '        m_aborted = true;\n'
                        '    };\n'
                        '    if (m_aborted)\n'
                        '        return;\n'
                        '    m_analysisFileOut = nullptr;\n',
                        1,
                    ),
                    PRINT_BLOCK,
                ),
            },
        )
        expect_fail(run_checker(root), 'writeAnalysisFileRefine must retire the failed stream before later aborted/null stream guards')

    print('Analysis output fail-state guard tests passed')


if __name__ == '__main__':
    main()
