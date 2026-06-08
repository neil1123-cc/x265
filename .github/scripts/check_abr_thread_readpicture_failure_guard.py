#!/usr/bin/env python3
import argparse
from pathlib import Path


ABR_TARGET = Path('source/abrEncApp.cpp')
ABR_REQUIRED_SNIPPETS = (
    'if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)',
    'else if (readPicture(pic_in[view], view)){',
    'else if (m_ret != 0)',
    'goto fail;',
    'else',
    'pic_in[view] = nullptr;',
    'if (m_input[view]->readPicture(*src))',
    'else if (m_input[view]->isFail())',
    'x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Reader input failed for view %d\\n", view);',
    'm_parentEnc->m_ret = 4;',
    'm_threadActive.store(false);',
    'm_parentEnc->m_inputOver.store(true);',
    'm_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
    'break;',
)
LAVF_TARGET = Path('source/input/lavf.cpp')
LAVF_REQUIRED_SNIPPETS = (
    'if (ret != AVERROR_EOF)',
    'general_log(nullptr, "lavf", X265_LOG_WARNING, "reading input failed on frame %d\\n", h->next_frame);',
    'general_log(nullptr, "lavf", X265_LOG_WARNING, "feeding input to decoder failed on frame %d\\n", h->next_frame);',
    'general_log(nullptr, "lavf", X265_LOG_WARNING, "video decoding failed on frame %d\\n", h->next_frame);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    abr_path = repo_root / ABR_TARGET
    if not abr_path.is_file():
        return [(ABR_TARGET.as_posix(), 0, 'missing file')]

    lavf_path = repo_root / LAVF_TARGET
    if not lavf_path.is_file():
        return [(LAVF_TARGET.as_posix(), 0, 'missing file')]

    abr_text = abr_path.read_text(encoding='utf-8', errors='ignore')
    lavf_text = lavf_path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in ABR_REQUIRED_SNIPPETS:
        if snippet not in abr_text:
            failures.append((ABR_TARGET.as_posix(), 0, f'missing ABR thread readPicture failure guardrail: {snippet}'))
    for snippet in LAVF_REQUIRED_SNIPPETS:
        if snippet not in lavf_text:
            failures.append((LAVF_TARGET.as_posix(), 0, f'missing lavf runtime failure guardrail: {snippet}'))

    frame_limit_pos = abr_text.find('if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)')
    read_pos = abr_text.find('else if (readPicture(pic_in[view], view)){', frame_limit_pos if frame_limit_pos != -1 else 0)
    fail_guard_pos = abr_text.find('else if (m_ret != 0)', read_pos if read_pos != -1 else 0)
    goto_fail_pos = abr_text.find('goto fail;', fail_guard_pos if fail_guard_pos != -1 else 0)
    eof_pos = abr_text.find('pic_in[view] = nullptr;', goto_fail_pos if goto_fail_pos != -1 else 0)
    if -1 in (frame_limit_pos, read_pos, fail_guard_pos, goto_fail_pos, eof_pos) or not (
        frame_limit_pos < read_pos < fail_guard_pos < goto_fail_pos < eof_pos
    ):
        failures.append((ABR_TARGET.as_posix(), 0, 'PassEncoder::threadMain must escalate readPicture failures before treating them as EOF'))

    reader_read_pos = abr_text.find('if (m_input[view]->readPicture(*src))')
    reader_fail_guard_pos = abr_text.find('else if (m_input[view]->isFail())', reader_read_pos if reader_read_pos != -1 else 0)
    reader_log_pos = abr_text.find('x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Reader input failed for view %d\\n", view);', reader_fail_guard_pos if reader_fail_guard_pos != -1 else 0)
    reader_ret_pos = abr_text.find('m_parentEnc->m_ret = 4;', reader_fail_guard_pos if reader_fail_guard_pos != -1 else 0)
    reader_stop_pos = abr_text.find('m_threadActive.store(false);', reader_fail_guard_pos if reader_fail_guard_pos != -1 else 0)
    reader_input_over_pos = abr_text.find('m_parentEnc->m_inputOver.store(true);', reader_stop_pos if reader_stop_pos != -1 else 0)
    reader_poke_pos = abr_text.find('m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();', reader_input_over_pos if reader_input_over_pos != -1 else 0)
    reader_break_pos = abr_text.find('break;', reader_poke_pos if reader_poke_pos != -1 else 0)
    reader_eof_else_pos = abr_text.find('else', reader_break_pos if reader_break_pos != -1 else 0)
    reader_eof_stop_pos = abr_text.find('m_threadActive.store(false);', reader_eof_else_pos if reader_eof_else_pos != -1 else 0)
    reader_eof_input_over_pos = abr_text.find('m_parentEnc->m_inputOver.store(true);', reader_eof_stop_pos if reader_eof_stop_pos != -1 else 0)
    reader_eof_poke_pos = abr_text.find('m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();', reader_eof_input_over_pos if reader_eof_input_over_pos != -1 else 0)
    reader_eof_break_pos = abr_text.find('break;', reader_eof_poke_pos if reader_eof_poke_pos != -1 else 0)
    if -1 in (
        reader_read_pos,
        reader_fail_guard_pos,
        reader_log_pos,
        reader_ret_pos,
        reader_stop_pos,
        reader_input_over_pos,
        reader_poke_pos,
        reader_break_pos,
        reader_eof_else_pos,
        reader_eof_stop_pos,
        reader_eof_input_over_pos,
        reader_eof_poke_pos,
        reader_eof_break_pos,
    ) or not (
        reader_read_pos < reader_fail_guard_pos < reader_log_pos < reader_ret_pos <
        reader_stop_pos < reader_input_over_pos < reader_poke_pos < reader_break_pos <
        reader_eof_else_pos < reader_eof_stop_pos < reader_eof_input_over_pos < reader_eof_poke_pos < reader_eof_break_pos
    ):
        failures.append((ABR_TARGET.as_posix(), 0, 'Reader::threadMain must escalate input read failures before treating them as EOF'))

    lavf_read_error_pos = lavf_text.find('if (ret != AVERROR_EOF)')
    lavf_read_log_pos = lavf_text.find('general_log(nullptr, "lavf", X265_LOG_WARNING, "reading input failed on frame %d\\n", h->next_frame);', lavf_read_error_pos if lavf_read_error_pos != -1 else 0)
    lavf_read_fail_flag_pos = lavf_text.find('b_fail = true;', lavf_read_log_pos if lavf_read_log_pos != -1 else 0)
    lavf_read_fail_pos = lavf_text.find('fail = 1;', lavf_read_fail_flag_pos if lavf_read_fail_flag_pos != -1 else 0)
    lavf_read_break_pos = lavf_text.find('break;', lavf_read_fail_pos if lavf_read_fail_pos != -1 else 0)
    feed_log_pos = lavf_text.find('general_log(nullptr, "lavf", X265_LOG_WARNING, "feeding input to decoder failed on frame %d\\n", h->next_frame);')
    feed_fail_flag_pos = lavf_text.find('b_fail = true;', feed_log_pos if feed_log_pos != -1 else 0)
    feed_fail_pos = lavf_text.find('fail = 1;', feed_fail_flag_pos if feed_fail_flag_pos != -1 else 0)
    decode_log_pos = lavf_text.find('general_log(nullptr, "lavf", X265_LOG_WARNING, "video decoding failed on frame %d\\n", h->next_frame);')
    decode_fail_flag_pos = lavf_text.find('b_fail = true;', decode_log_pos if decode_log_pos != -1 else 0)
    decode_fail_pos = lavf_text.find('fail = 1;', decode_fail_flag_pos if decode_fail_flag_pos != -1 else 0)
    if -1 in (
        lavf_read_error_pos,
        lavf_read_log_pos,
        lavf_read_fail_flag_pos,
        lavf_read_fail_pos,
        lavf_read_break_pos,
        feed_log_pos,
        feed_fail_flag_pos,
        feed_fail_pos,
        decode_log_pos,
        decode_fail_flag_pos,
        decode_fail_pos,
    ) or not (
        lavf_read_error_pos < lavf_read_log_pos < lavf_read_fail_flag_pos < lavf_read_fail_pos < lavf_read_break_pos and
        feed_log_pos < feed_fail_flag_pos < feed_fail_pos and
        decode_log_pos < decode_fail_flag_pos < decode_fail_pos
    ):
        failures.append((LAVF_TARGET.as_posix(), 0, 'LavfInput::readPicture must persist runtime read/decode failures to b_fail'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread readPicture failure guard')
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

    print('ABR thread readPicture failure guard validated')


if __name__ == '__main__':
    main()
