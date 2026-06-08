#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_readpicture_failure_guard.py')


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


def valid_abr_text():
    return '\n'.join((
        'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
        '    pic_in[view] = nullptr;',
        'else if (readPicture(pic_in[view], view)){',
        '    if(view == viewCount - 1)',
        '        inFrameCount++;',
        '}',
        'else if (m_ret != 0)',
        '    goto fail;',
        'else',
        '    pic_in[view] = nullptr;',
        'if (m_input[view]->readPicture(*src))',
        '    m_parentEnc->m_parent->m_picWriteCnt[m_id].incr();',
        'else if (m_input[view]->isFail())',
        '{',
        '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Reader input failed for view %d\\n", view);',
        '    m_parentEnc->m_ret = 4;',
        '    m_threadActive.store(false);',
        '    m_parentEnc->m_inputOver.store(true);',
        '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
        '    break;',
        '}',
        'else',
        '{',
        '    m_threadActive.store(false);',
        '    m_parentEnc->m_inputOver.store(true);',
        '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
        '    break;',
        '}',
    )) + '\n'


def valid_lavf_text():
    return '\n'.join((
        'if(ret < 0)',
        '{',
        '    av_packet_unref(pkt);',
        '    if (ret != AVERROR_EOF)',
        '    {',
        '        general_log(nullptr, "lavf", X265_LOG_WARNING, "reading input failed on frame %d\\n", h->next_frame);',
        '        b_fail = true;',
        '        fail = 1;',
        '        break;',
        '    }',
        '}',
        'if(codec_ret == AVERROR(EINVAL))',
        '{',
        '    general_log(nullptr, "lavf", X265_LOG_WARNING, "feeding input to decoder failed on frame %d\\n", h->next_frame);',
        '    b_fail = true;',
        '    fail = 1;',
        '}',
        'if(codec_ret == AVERROR(EINVAL))',
        '{',
        '    general_log(nullptr, "lavf", X265_LOG_WARNING, "video decoding failed on frame %d\\n", h->next_frame);',
        '    b_fail = true;',
        '    fail = 1;',
        '}',
    )) + '\n'


def valid_repo():
    return {
        'source/abrEncApp.cpp': valid_abr_text(),
        'source/input/lavf.cpp': valid_lavf_text(),
    }


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, valid_repo())
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': valid_abr_text().replace('else if (m_ret != 0)\n    goto fail;\n', '', 1),
                'source/input/lavf.cpp': valid_lavf_text(),
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread readPicture failure guardrail: else if (m_ret != 0)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
                    '    pic_in[view] = nullptr;',
                    'else if (readPicture(pic_in[view], view)){',
                    '    if(view == viewCount - 1)',
                    '        inFrameCount++;',
                    '}',
                    'else',
                    '    pic_in[view] = nullptr;',
                    'goto fail;',
                )) + '\n',
                'source/input/lavf.cpp': valid_lavf_text(),
            },
        )
        expect_fail(run_checker(root), 'PassEncoder::threadMain must escalate readPicture failures before treating them as EOF')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
                    '    pic_in[view] = nullptr;',
                    'else if (readPicture(pic_in[view], view)){',
                    '    if(view == viewCount - 1)',
                    '        inFrameCount++;',
                    '}',
                    'else if (m_ret != 0)',
                    '    goto fail;',
                    'else',
                    '    pic_in[view] = nullptr;',
                    'if (m_input[view]->readPicture(*src))',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].incr();',
                    'else',
                    '{',
                    '    m_threadActive.store(false);',
                    '    m_parentEnc->m_inputOver.store(true);',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '    break;',
                    '}',
                )) + '\n',
                'source/input/lavf.cpp': valid_lavf_text(),
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread readPicture failure guardrail: else if (m_input[view]->isFail())')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
                    '    pic_in[view] = nullptr;',
                    'else if (readPicture(pic_in[view], view)){',
                    '    if(view == viewCount - 1)',
                    '        inFrameCount++;',
                    '}',
                    'else if (m_ret != 0)',
                    '    goto fail;',
                    'else',
                    '    pic_in[view] = nullptr;',
                    'if (m_input[view]->readPicture(*src))',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].incr();',
                    'else',
                    '{',
                    '    m_threadActive.store(false);',
                    '    m_parentEnc->m_inputOver.store(true);',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '    break;',
                    '}',
                    'else if (m_input[view]->isFail())',
                    '{',
                    '    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Reader input failed for view %d\\n", view);',
                    '    m_parentEnc->m_ret = 4;',
                    '    m_threadActive.store(false);',
                    '    m_parentEnc->m_inputOver.store(true);',
                    '    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
                    '    break;',
                    '}',
                )) + '\n',
                'source/input/lavf.cpp': valid_lavf_text(),
            },
        )
        expect_fail(run_checker(root), 'Reader::threadMain must escalate input read failures before treating them as EOF')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': valid_abr_text(),
                'source/input/lavf.cpp': '\n'.join((
                    'if(ret < 0)',
                    '{',
                    '    av_packet_unref(pkt);',
                    '}',
                    'if(codec_ret == AVERROR(EINVAL))',
                    '{',
                    '    general_log(nullptr, "lavf", X265_LOG_WARNING, "feeding input to decoder failed on frame %d\\n", h->next_frame);',
                    '    b_fail = true;',
                    '    fail = 1;',
                    '}',
                    'if(codec_ret == AVERROR(EINVAL))',
                    '{',
                    '    general_log(nullptr, "lavf", X265_LOG_WARNING, "video decoding failed on frame %d\\n", h->next_frame);',
                    '    b_fail = true;',
                    '    fail = 1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing lavf runtime failure guardrail: if (ret != AVERROR_EOF)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': valid_abr_text(),
                'source/input/lavf.cpp': '\n'.join((
                    'if(ret < 0)',
                    '{',
                    '    av_packet_unref(pkt);',
                    '    if (ret != AVERROR_EOF)',
                    '    {',
                    '        general_log(nullptr, "lavf", X265_LOG_WARNING, "reading input failed on frame %d\\n", h->next_frame);',
                    '        fail = 1;',
                    '        break;',
                    '    }',
                    '}',
                    'if(codec_ret == AVERROR(EINVAL))',
                    '{',
                    '    general_log(nullptr, "lavf", X265_LOG_WARNING, "feeding input to decoder failed on frame %d\\n", h->next_frame);',
                    '    fail = 1;',
                    '}',
                    'if(codec_ret == AVERROR(EINVAL))',
                    '{',
                    '    general_log(nullptr, "lavf", X265_LOG_WARNING, "video decoding failed on frame %d\\n", h->next_frame);',
                    '    b_fail = true;',
                    '    fail = 1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'LavfInput::readPicture must persist runtime read/decode failures to b_fail')

    print('ABR thread readPicture failure guard tests passed')


if __name__ == '__main__':
    main()
