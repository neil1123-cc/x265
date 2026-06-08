#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'x265_picture *srcPic = m_parentEnc->m_parent->m_inputPicBuffer[srcId][scaledWritten % QDepth];',
    'x265_picture* destPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];',
    'if (!srcPic || !destPic)',
    'x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing scaler queue picture at src %u dst %d\\n", scaledWritten % QDepth, scaledWriteIdx);',
    'if (!scalePic(destPic, srcPic))',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to copy scaled input picture to input queue \\n");',
    'm_parentEnc->m_ret = 4;',
    'm_threadActive.store(false);',
    'm_parentEnc->m_inputOver.store(true);',
    'm_parentEnc->m_parent->m_picWriteCnt[srcId].poke();',
    'm_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
    'm_parentEnc->m_parent->m_picWriteCnt[m_id].incr();',
    'm_scaledWriteCnt.incr();',
    'm_parentEnc->m_parent->m_picIdxReadCnt[srcId][scaledWriteIdx].incr();',
    'x265_picture* dest = m_parentEnc->m_parent->m_inputPicBuffer[m_id][writeIdx];',
    'if (m_parentEnc->m_param->numViews > 1)',
    'dest = m_parentEnc->m_parent->m_inputPicBuffer[view][writeIdx];',
    'if (!dest)',
    'x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader queue picture at view %d index %u\\n", view, writeIdx);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR queue picture guardrail: {snippet}'))

    def extract_braced_block(signature):
        start = text.find(signature)
        if start == -1:
            return text
        brace_start = text.find('{', start)
        if brace_start == -1:
            return text[start:]
        depth = 0
        for idx in range(brace_start, len(text)):
            char = text[idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        return text[start:]

    scaler_text = extract_braced_block('void Scaler::threadMain()')
    reader_text = extract_braced_block('void Reader::threadMain()')

    src_pos = scaler_text.find('x265_picture *srcPic = m_parentEnc->m_parent->m_inputPicBuffer[srcId][scaledWritten % QDepth];')
    dest_pic_pos = scaler_text.find('x265_picture* destPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];', src_pos if src_pos != -1 else 0)
    scaler_guard_pos = scaler_text.find('if (!srcPic || !destPic)', dest_pic_pos if dest_pic_pos != -1 else 0)
    scale_pos = scaler_text.find('if (!scalePic(destPic, srcPic))', scaler_guard_pos if scaler_guard_pos != -1 else 0)
    fail_log_pos = scaler_text.find('x265_log(nullptr, X265_LOG_ERROR, "Unable to copy scaled input picture to input queue \\n");', scale_pos if scale_pos != -1 else 0)
    fail_ret_pos = scaler_text.find('m_parentEnc->m_ret = 4;', fail_log_pos if fail_log_pos != -1 else 0)
    fail_stop_pos = scaler_text.find('m_threadActive.store(false);', fail_ret_pos if fail_ret_pos != -1 else 0)
    fail_input_over_pos = scaler_text.find('m_parentEnc->m_inputOver.store(true);', fail_stop_pos if fail_stop_pos != -1 else 0)
    fail_src_poke_pos = scaler_text.find('m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();', fail_input_over_pos if fail_input_over_pos != -1 else 0)
    fail_dst_poke_pos = scaler_text.find('m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();', fail_src_poke_pos if fail_src_poke_pos != -1 else 0)
    fail_break_pos = scaler_text.find('break;', fail_dst_poke_pos if fail_dst_poke_pos != -1 else 0)
    publish_pos = scaler_text.find('m_parentEnc->m_parent->m_picWriteCnt[m_id].incr();', fail_break_pos if fail_break_pos != -1 else 0)
    scaled_count_pos = scaler_text.find('m_scaledWriteCnt.incr();', publish_pos if publish_pos != -1 else 0)
    src_read_count_pos = scaler_text.find('m_parentEnc->m_parent->m_picIdxReadCnt[srcId][scaledWriteIdx].incr();', scaled_count_pos if scaled_count_pos != -1 else 0)
    if -1 in (
        src_pos,
        dest_pic_pos,
        scaler_guard_pos,
        scale_pos,
        fail_log_pos,
        fail_ret_pos,
        fail_stop_pos,
        fail_input_over_pos,
        fail_src_poke_pos,
        fail_dst_poke_pos,
        fail_break_pos,
        publish_pos,
        scaled_count_pos,
        src_read_count_pos,
    ) or not (
        src_pos < dest_pic_pos < scaler_guard_pos < scale_pos < fail_log_pos < fail_ret_pos <
        fail_stop_pos < fail_input_over_pos < fail_src_poke_pos < fail_dst_poke_pos < fail_break_pos <
        publish_pos < scaled_count_pos < src_read_count_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Scaler::threadMain must guard srcPic/destPic before scalePic()'))
        failures.append((TARGET.as_posix(), 0, 'Scaler::threadMain must stop and surface scalePic() failures before advancing queue state'))

    reader_dest_pos = reader_text.find('x265_picture* dest = m_parentEnc->m_parent->m_inputPicBuffer[m_id][writeIdx];')
    reader_multiview_pos = reader_text.find('if (m_parentEnc->m_param->numViews > 1)', reader_dest_pos if reader_dest_pos != -1 else 0)
    reader_redirect_pos = reader_text.find('dest = m_parentEnc->m_parent->m_inputPicBuffer[view][writeIdx];', reader_multiview_pos if reader_multiview_pos != -1 else 0)
    reader_guard_pos = reader_text.find('if (!dest)', reader_redirect_pos if reader_redirect_pos != -1 else 0)
    read_pos = reader_text.find('if (m_input[view]->readPicture(*src))', reader_guard_pos if reader_guard_pos != -1 else 0)
    if -1 in (reader_dest_pos, reader_multiview_pos, reader_redirect_pos, reader_guard_pos, read_pos) or not (reader_dest_pos < reader_multiview_pos < reader_redirect_pos < reader_guard_pos < read_pos):
        failures.append((TARGET.as_posix(), 0, 'Reader::threadMain must select and guard dest before readPicture(*src)'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR queue picture guards')
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

    print('ABR queue picture guards validated')


if __name__ == '__main__':
    main()
