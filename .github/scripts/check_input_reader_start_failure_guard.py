#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = {
    Path('source/input/y4m.h'): (
        'std::atomic<bool> failed;',
        'bool isFail()                 { return failed.load() || (ifs && std::ferror(ifs)); }',
    ),
    Path('source/input/y4m.cpp'): (
        'failed.store(true);',
        'failed.store(!threadActive.load());',
        'x265_log(nullptr, X265_LOG_ERROR, "y4m: skip offset exceeds supported range\\n");',
        'x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to skip requested frames\\n");',
        'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame header truncated\\n" : "y4m: skip frame header read failed\\n");',
        'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame payload truncated\\n" : "y4m: skip frame payload read failed\\n");',
        'if (threadActive.load() && !start())',
        'x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to start reader thread\\n");',
        'failed.store(true);',
        'threadActive.store(false);',
        'writeCount.poke();',
        'size_t headerBytes = std::fread(hbuf, 1, sizeof(hbuf), ifs);',
        'if (!headerBytes && std::feof(ifs))',
        'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header missing\\n");',
        'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header truncated\\n");',
        'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: frame payload truncated\\n" : "y4m: frame payload read failed\\n");',
    ),
    Path('source/input/yuv.h'): (
        'std::atomic<bool> failed;',
        'bool isFail()                                 { return failed.load() || (ifs && std::ferror(ifs)); }',
    ),
    Path('source/input/yuv.cpp'): (
        'failed.store(true);',
        'failed.store(!threadActive.load());',
        'x265_log(nullptr, X265_LOG_ERROR, "yuv: skip offset exceeds supported range\\n");',
        'x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to skip requested frames\\n");',
        'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: skip frame payload truncated\\n" : "yuv: skip frame payload read failed\\n");',
        'if (threadActive.load() && !start())',
        'x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to start reader thread\\n");',
        'failed.store(true);',
        'threadActive.store(false);',
        'writeCount.poke();',
        'size_t frameBytes = std::fread(buf[written % QUEUE_SIZE], 1, framesize, ifs);',
        'if (!frameBytes && std::feof(ifs))',
        'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: frame payload truncated\\n" : "yuv: frame payload read failed\\n");',
    ),
    Path('source/x265cli.cpp'): (
        'this->input[view]->startReader();',
        'if (this->input[view]->isFail())',
        'x265_log_file(param, X265_LOG_ERROR, "unable to start input reader for <%s>\\n", inputfn[view]);',
        'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
        'return true;',
    ),
}


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    for target, snippets in TARGETS.items():
        path = repo_root / target
        if not path.is_file():
            failures.append((target.as_posix(), 0, 'missing file'))
            continue

        text = path.read_text(encoding='utf-8', errors='ignore')
        for snippet in snippets:
            if snippet not in text:
                failures.append((target.as_posix(), 0, f'missing input reader start failure guardrail: {snippet}'))

    y4m_text = (repo_root / Path('source/input/y4m.cpp')).read_text(encoding='utf-8', errors='ignore')
    y4m_start_pos = y4m_text.find('if (threadActive.load() && !start())')
    y4m_log_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to start reader thread\\n");', y4m_start_pos if y4m_start_pos != -1 else 0)
    y4m_fail_pos = y4m_text.find('failed.store(true);', y4m_log_pos if y4m_log_pos != -1 else 0)
    y4m_clear_pos = y4m_text.find('threadActive.store(false);', y4m_fail_pos if y4m_fail_pos != -1 else 0)
    y4m_poke_pos = y4m_text.find('writeCount.poke();', y4m_clear_pos if y4m_clear_pos != -1 else 0)
    if -1 in (y4m_start_pos, y4m_log_pos, y4m_fail_pos, y4m_clear_pos, y4m_poke_pos) or not (y4m_start_pos < y4m_log_pos < y4m_fail_pos < y4m_clear_pos < y4m_poke_pos):
        failures.append(('source/input/y4m.cpp', 0, 'Y4MInput::startReader must mark startup failure before clearing threadActive and waking readers'))

    y4m_header_bytes_pos = y4m_text.find('size_t headerBytes = std::fread(hbuf, 1, sizeof(hbuf), ifs);')
    y4m_eof_guard_pos = y4m_text.find('if (!headerBytes && std::feof(ifs))', y4m_header_bytes_pos if y4m_header_bytes_pos != -1 else 0)
    y4m_header_fail_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header missing\\n");', y4m_eof_guard_pos if y4m_eof_guard_pos != -1 else 0)
    y4m_header_flag_pos = y4m_text.find('failed.store(true);', y4m_header_fail_pos if y4m_header_fail_pos != -1 else 0)
    y4m_header_return_pos = y4m_text.find('return false;', y4m_header_flag_pos if y4m_header_flag_pos != -1 else 0)
    y4m_truncated_fail_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header truncated\\n");', y4m_header_return_pos if y4m_header_return_pos != -1 else 0)
    y4m_truncated_flag_pos = y4m_text.find('failed.store(true);', y4m_truncated_fail_pos if y4m_truncated_fail_pos != -1 else 0)
    y4m_truncated_return_pos = y4m_text.find('return false;', y4m_truncated_flag_pos if y4m_truncated_flag_pos != -1 else 0)
    y4m_payload_fail_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: frame payload truncated\\n" : "y4m: frame payload read failed\\n");', y4m_truncated_return_pos if y4m_truncated_return_pos != -1 else 0)
    y4m_payload_flag_pos = y4m_text.find('failed.store(true);', y4m_payload_fail_pos if y4m_payload_fail_pos != -1 else 0)
    y4m_payload_return_pos = y4m_text.find('return false;', y4m_payload_flag_pos if y4m_payload_flag_pos != -1 else 0)
    if -1 in (
        y4m_header_bytes_pos,
        y4m_eof_guard_pos,
        y4m_header_fail_pos,
        y4m_header_flag_pos,
        y4m_header_return_pos,
        y4m_truncated_fail_pos,
        y4m_truncated_flag_pos,
        y4m_truncated_return_pos,
        y4m_payload_fail_pos,
        y4m_payload_flag_pos,
        y4m_payload_return_pos,
    ) or not (
        y4m_header_bytes_pos < y4m_eof_guard_pos < y4m_header_fail_pos < y4m_header_flag_pos < y4m_header_return_pos <
        y4m_truncated_fail_pos < y4m_truncated_flag_pos < y4m_truncated_return_pos <
        y4m_payload_fail_pos < y4m_payload_flag_pos < y4m_payload_return_pos
    ):
        failures.append(('source/input/y4m.cpp', 0, 'Y4MInput::populateFrameQueue must distinguish clean EOF from corrupt/truncated frame headers and payloads'))

    y4m_skip_range_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, "y4m: skip offset exceeds supported range\\n");')
    y4m_skip_range_flag_pos = y4m_text.find('failed.store(true);', y4m_skip_range_pos if y4m_skip_range_pos != -1 else 0)
    y4m_skip_range_clear_pos = y4m_text.find('threadActive.store(false);', y4m_skip_range_flag_pos if y4m_skip_range_flag_pos != -1 else 0)
    y4m_skip_seek_fail_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to skip requested frames\\n");', y4m_skip_range_clear_pos if y4m_skip_range_clear_pos != -1 else 0)
    y4m_skip_seek_flag_pos = y4m_text.find('failed.store(true);', y4m_skip_seek_fail_pos if y4m_skip_seek_fail_pos != -1 else 0)
    y4m_skip_seek_clear_pos = y4m_text.find('threadActive.store(false);', y4m_skip_seek_flag_pos if y4m_skip_seek_flag_pos != -1 else 0)
    y4m_skip_header_fail_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame header truncated\\n" : "y4m: skip frame header read failed\\n");', y4m_skip_seek_clear_pos if y4m_skip_seek_clear_pos != -1 else 0)
    y4m_skip_header_flag_pos = y4m_text.find('failed.store(true);', y4m_skip_header_fail_pos if y4m_skip_header_fail_pos != -1 else 0)
    y4m_skip_header_clear_pos = y4m_text.find('threadActive.store(false);', y4m_skip_header_flag_pos if y4m_skip_header_flag_pos != -1 else 0)
    y4m_skip_header_break_pos = y4m_text.find('break;', y4m_skip_header_clear_pos if y4m_skip_header_clear_pos != -1 else 0)
    y4m_skip_payload_fail_pos = y4m_text.find('x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame payload truncated\\n" : "y4m: skip frame payload read failed\\n");', y4m_skip_header_break_pos if y4m_skip_header_break_pos != -1 else 0)
    y4m_skip_payload_flag_pos = y4m_text.find('failed.store(true);', y4m_skip_payload_fail_pos if y4m_skip_payload_fail_pos != -1 else 0)
    y4m_skip_payload_clear_pos = y4m_text.find('threadActive.store(false);', y4m_skip_payload_flag_pos if y4m_skip_payload_flag_pos != -1 else 0)
    y4m_skip_payload_break_pos = y4m_text.find('break;', y4m_skip_payload_clear_pos if y4m_skip_payload_clear_pos != -1 else 0)
    if -1 in (
        y4m_skip_range_pos,
        y4m_skip_range_flag_pos,
        y4m_skip_range_clear_pos,
        y4m_skip_seek_fail_pos,
        y4m_skip_seek_flag_pos,
        y4m_skip_seek_clear_pos,
        y4m_skip_header_fail_pos,
        y4m_skip_header_flag_pos,
        y4m_skip_header_clear_pos,
        y4m_skip_header_break_pos,
        y4m_skip_payload_fail_pos,
        y4m_skip_payload_flag_pos,
        y4m_skip_payload_clear_pos,
        y4m_skip_payload_break_pos,
    ) or not (
        y4m_skip_range_pos < y4m_skip_range_flag_pos < y4m_skip_range_clear_pos <
        y4m_skip_seek_fail_pos < y4m_skip_seek_flag_pos < y4m_skip_seek_clear_pos <
        y4m_skip_header_fail_pos < y4m_skip_header_flag_pos < y4m_skip_header_clear_pos < y4m_skip_header_break_pos <
        y4m_skip_payload_fail_pos < y4m_skip_payload_flag_pos < y4m_skip_payload_clear_pos < y4m_skip_payload_break_pos
    ):
        failures.append(('source/input/y4m.cpp', 0, 'Y4MInput constructor must surface skip seek/read failures before leaving the reader active'))

    yuv_text = (repo_root / Path('source/input/yuv.cpp')).read_text(encoding='utf-8', errors='ignore')
    yuv_start_pos = yuv_text.find('if (threadActive.load() && !start())')
    yuv_log_pos = yuv_text.find('x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to start reader thread\\n");', yuv_start_pos if yuv_start_pos != -1 else 0)
    yuv_fail_pos = yuv_text.find('failed.store(true);', yuv_log_pos if yuv_log_pos != -1 else 0)
    yuv_clear_pos = yuv_text.find('threadActive.store(false);', yuv_fail_pos if yuv_fail_pos != -1 else 0)
    yuv_poke_pos = yuv_text.find('writeCount.poke();', yuv_clear_pos if yuv_clear_pos != -1 else 0)
    if -1 in (yuv_start_pos, yuv_log_pos, yuv_fail_pos, yuv_clear_pos, yuv_poke_pos) or not (yuv_start_pos < yuv_log_pos < yuv_fail_pos < yuv_clear_pos < yuv_poke_pos):
        failures.append(('source/input/yuv.cpp', 0, 'YUVInput::startReader must mark startup failure before clearing threadActive and waking readers'))

    yuv_frame_bytes_pos = yuv_text.find('size_t frameBytes = std::fread(buf[written % QUEUE_SIZE], 1, framesize, ifs);')
    yuv_eof_guard_pos = yuv_text.find('if (!frameBytes && std::feof(ifs))', yuv_frame_bytes_pos if yuv_frame_bytes_pos != -1 else 0)
    yuv_payload_fail_pos = yuv_text.find('x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: frame payload truncated\\n" : "yuv: frame payload read failed\\n");', yuv_eof_guard_pos if yuv_eof_guard_pos != -1 else 0)
    yuv_payload_flag_pos = yuv_text.find('failed.store(true);', yuv_payload_fail_pos if yuv_payload_fail_pos != -1 else 0)
    yuv_payload_return_pos = yuv_text.find('return false;', yuv_payload_flag_pos if yuv_payload_flag_pos != -1 else 0)
    if -1 in (
        yuv_frame_bytes_pos,
        yuv_eof_guard_pos,
        yuv_payload_fail_pos,
        yuv_payload_flag_pos,
        yuv_payload_return_pos,
    ) or not (
        yuv_frame_bytes_pos < yuv_eof_guard_pos < yuv_payload_fail_pos < yuv_payload_flag_pos < yuv_payload_return_pos
    ):
        failures.append(('source/input/yuv.cpp', 0, 'YUVInput::populateFrameQueue must distinguish clean EOF from truncated frame payloads'))

    yuv_skip_range_pos = yuv_text.find('x265_log(nullptr, X265_LOG_ERROR, "yuv: skip offset exceeds supported range\\n");')
    yuv_skip_range_flag_pos = yuv_text.find('failed.store(true);', yuv_skip_range_pos if yuv_skip_range_pos != -1 else 0)
    yuv_skip_range_clear_pos = yuv_text.find('threadActive.store(false);', yuv_skip_range_flag_pos if yuv_skip_range_flag_pos != -1 else 0)
    yuv_skip_seek_fail_pos = yuv_text.find('x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to skip requested frames\\n");', yuv_skip_range_clear_pos if yuv_skip_range_clear_pos != -1 else 0)
    yuv_skip_seek_flag_pos = yuv_text.find('failed.store(true);', yuv_skip_seek_fail_pos if yuv_skip_seek_fail_pos != -1 else 0)
    yuv_skip_seek_clear_pos = yuv_text.find('threadActive.store(false);', yuv_skip_seek_flag_pos if yuv_skip_seek_flag_pos != -1 else 0)
    yuv_skip_payload_fail_pos = yuv_text.find('x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: skip frame payload truncated\\n" : "yuv: skip frame payload read failed\\n");', yuv_skip_seek_clear_pos if yuv_skip_seek_clear_pos != -1 else 0)
    yuv_skip_payload_flag_pos = yuv_text.find('failed.store(true);', yuv_skip_payload_fail_pos if yuv_skip_payload_fail_pos != -1 else 0)
    yuv_skip_payload_clear_pos = yuv_text.find('threadActive.store(false);', yuv_skip_payload_flag_pos if yuv_skip_payload_flag_pos != -1 else 0)
    yuv_skip_payload_break_pos = yuv_text.find('break;', yuv_skip_payload_clear_pos if yuv_skip_payload_clear_pos != -1 else 0)
    if -1 in (
        yuv_skip_range_pos,
        yuv_skip_range_flag_pos,
        yuv_skip_range_clear_pos,
        yuv_skip_seek_fail_pos,
        yuv_skip_seek_flag_pos,
        yuv_skip_seek_clear_pos,
        yuv_skip_payload_fail_pos,
        yuv_skip_payload_flag_pos,
        yuv_skip_payload_clear_pos,
        yuv_skip_payload_break_pos,
    ) or not (
        yuv_skip_range_pos < yuv_skip_range_flag_pos < yuv_skip_range_clear_pos <
        yuv_skip_seek_fail_pos < yuv_skip_seek_flag_pos < yuv_skip_seek_clear_pos <
        yuv_skip_payload_fail_pos < yuv_skip_payload_flag_pos < yuv_skip_payload_clear_pos < yuv_skip_payload_break_pos
    ):
        failures.append(('source/input/yuv.cpp', 0, 'YUVInput constructor must surface skip seek/read failures before leaving the reader active'))

    cli_text = (repo_root / Path('source/x265cli.cpp')).read_text(encoding='utf-8', errors='ignore')
    cli_start_pos = cli_text.find('this->input[view]->startReader();')
    cli_fail_pos = cli_text.find('if (this->input[view]->isFail())', cli_start_pos if cli_start_pos != -1 else 0)
    cli_log_pos = cli_text.find('x265_log_file(param, X265_LOG_ERROR, "unable to start input reader for <%s>\\n", inputfn[view]);', cli_fail_pos if cli_fail_pos != -1 else 0)
    cli_release_pos = cli_text.find('for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)', cli_log_pos if cli_log_pos != -1 else 0)
    cli_return_pos = cli_text.find('return true;', cli_release_pos if cli_release_pos != -1 else 0)
    if -1 in (cli_start_pos, cli_fail_pos, cli_log_pos, cli_release_pos, cli_return_pos) or not (cli_start_pos < cli_fail_pos < cli_log_pos < cli_release_pos < cli_return_pos):
        failures.append(('source/x265cli.cpp', 0, 'CLIOptions::parse must fail fast and release inputs when an input reader thread fails to start'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check input reader start failure handling guardrails')
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

    print('Input reader start failure handling validated')


if __name__ == '__main__':
    main()
