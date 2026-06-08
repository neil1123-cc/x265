#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
FORBIDDEN_SNIPPETS = (
    'm_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx] = x265_picture_alloc();',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate scaled input picture\\n");',
    'm_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWritten % QDepth]->planes[j] = X265_MALLOC(char, planesize[j]);',
    'if (!m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWritten % QDepth]->planes[j])',
    'for (int32_t k = 0; k < j; k++)',
    'X265_FREE(m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWritten % QDepth]->planes[k]);',
    'x265_picture_free(m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx]);',
    'm_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx] = nullptr;',
)
REQUIRED_SNIPPETS = (
    'if (!m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx])',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate scaled input picture slot\\n");',
    'm_parentEnc->m_ret = 4;',
    'm_parentEnc->m_inputOver.store(true);',
    'm_parentEnc->m_parent->m_picWriteCnt[srcId].poke();',
    'm_parentEnc->m_parent->m_picWriteCnt[m_id].poke();',
    'x265_picture* scaledPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];',
    'if (!scaledPic->planes[0] || scaledPic->framesize != (size_t)frameSize)',
    'X265_FREE(scaledPic->planes[0]);',
    'scaledPic->planes[0] = X265_MALLOC(char, frameSize);',
    'if (!scaledPic->planes[0])',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate scaled input plane\\n");',
    'scaledPic->planes[1] = nullptr;',
    'scaledPic->planes[2] = nullptr;',
    'scaledPic->planes[3] = nullptr;',
    'scaledPic->framesize = 0;',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden scaler thread alloc regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing scaler thread alloc guardrail: {snippet}'))

    slot_guard_pos = text.find('if (!m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx])')
    scaled_pic_pos = text.find('x265_picture* scaledPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];', slot_guard_pos)
    if -1 not in (slot_guard_pos, scaled_pic_pos) and not (slot_guard_pos < scaled_pic_pos):
        failures.append((TARGET.as_posix(), 0, 'Scaler::threadMain must validate the preallocated picture slot before dereferencing it'))

    plane_resize_guard_pos = text.find('if (!scaledPic->planes[0] || scaledPic->framesize != (size_t)frameSize)')
    plane_alloc_pos = text.find('scaledPic->planes[0] = X265_MALLOC(char, frameSize);', plane_resize_guard_pos)
    plane_guard_pos = text.find('if (!scaledPic->planes[0])', plane_alloc_pos)
    if -1 not in (plane_resize_guard_pos, plane_alloc_pos, plane_guard_pos):
        if not (plane_resize_guard_pos < plane_alloc_pos < plane_guard_pos):
            failures.append((TARGET.as_posix(), 0, 'Scaler::threadMain must guard frame-size-driven plane reallocation immediately after X265_MALLOC'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Scaler::threadMain allocation guards')
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

    print('Scaler thread allocation guards validated')


if __name__ == '__main__':
    main()
