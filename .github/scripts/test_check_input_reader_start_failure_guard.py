#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_input_reader_start_failure_guard.py')

# Coverage probes used by the scan for input reader start failure guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'Y4MInput::startReader must mark startup failure before clearing threadActive and waking readers',
    'YUVInput::startReader must mark startup failure before clearing threadActive and waking readers',
    'CLIOptions::parse must fail fast and release inputs when an input reader thread fails to start',
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
                'source/input/y4m.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/y4m.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: skip offset exceeds supported range\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to skip requested frames\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame header truncated\\n" : "y4m: skip frame header read failed\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'break;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame payload truncated\\n" : "y4m: skip frame payload read failed\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'break;',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t headerBytes = std::fread(hbuf, 1, sizeof(hbuf), ifs);',
                    'if (!headerBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header missing\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header truncated\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: frame payload truncated\\n" : "y4m: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/input/yuv.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/yuv.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'x265_log(nullptr, X265_LOG_ERROR, "yuv: skip offset exceeds supported range\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to skip requested frames\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: skip frame payload truncated\\n" : "yuv: skip frame payload read failed\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'break;',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t frameBytes = std::fread(buf[written % QUEUE_SIZE], 1, framesize, ifs);',
                    'if (!frameBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: frame payload truncated\\n" : "yuv: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/x265cli.cpp': '\n'.join((
                    'this->input[view]->startReader();',
                    'if (this->input[view]->isFail())',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, "unable to start input reader for <%s>\\n", inputfn[view]);',
                    '    for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '    {',
                    '        if (this->input[releaseIdx])',
                    '        {',
                    '            this->input[releaseIdx]->release();',
                    '            this->input[releaseIdx] = nullptr;',
                    '        }',
                    '    }',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.h': 'bool isFail() { return false; }\n',
                'source/input/y4m.cpp': 'if (threadActive.load())\n    start();\n',
                'source/input/yuv.h': 'bool isFail() { return false; }\n',
                'source/input/yuv.cpp': 'if (threadActive.load())\n    start();\n',
                'source/x265cli.cpp': 'this->input[view]->startReader();\n',
            },
        )
        expect_fail(run_checker(root), 'missing input reader start failure guardrail: std::atomic<bool> failed;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/y4m.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t headerBytes = std::fread(hbuf, 1, sizeof(hbuf), ifs);',
                    'if (!headerBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header missing\\n");',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header truncated\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: frame payload truncated\\n" : "y4m: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/input/yuv.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/yuv.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t frameBytes = std::fread(buf[written % QUEUE_SIZE], 1, framesize, ifs);',
                    'if (!frameBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: frame payload truncated\\n" : "yuv: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/x265cli.cpp': '\n'.join((
                    'this->input[view]->startReader();',
                    'if (this->input[view]->isFail())',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, "unable to start input reader for <%s>\\n", inputfn[view]);',
                    '    for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '    {',
                    '        if (this->input[releaseIdx])',
                    '        {',
                    '            this->input[releaseIdx]->release();',
                    '            this->input[releaseIdx] = nullptr;',
                    '        }',
                    '    }',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Y4MInput::populateFrameQueue must distinguish clean EOF from corrupt/truncated frame headers and payloads')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/y4m.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t headerBytes = std::fread(hbuf, 1, sizeof(hbuf), ifs);',
                    'if (!headerBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header missing\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header truncated\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: frame payload truncated\\n" : "y4m: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/input/yuv.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/yuv.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t frameBytes = std::fread(buf[written % QUEUE_SIZE], 1, framesize, ifs);',
                    'if (!frameBytes && std::feof(ifs))',
                    '    return false;',
                    'return false;',
                )) + '\n',
                'source/x265cli.cpp': '\n'.join((
                    'this->input[view]->startReader();',
                    'if (this->input[view]->isFail())',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, "unable to start input reader for <%s>\\n", inputfn[view]);',
                    '    for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '    {',
                    '        if (this->input[releaseIdx])',
                    '        {',
                    '            this->input[releaseIdx]->release();',
                    '            this->input[releaseIdx] = nullptr;',
                    '        }',
                    '    }',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'YUVInput::populateFrameQueue must distinguish clean EOF from truncated frame payloads')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/y4m.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: skip offset exceeds supported range\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to skip requested frames\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame header truncated\\n" : "y4m: skip frame header read failed\\n");',
                    'threadActive.store(false);',
                    'break;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame payload truncated\\n" : "y4m: skip frame payload read failed\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'break;',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t headerBytes = std::fread(hbuf, 1, sizeof(hbuf), ifs);',
                    'if (!headerBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header missing\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header truncated\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: frame payload truncated\\n" : "y4m: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/input/yuv.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/yuv.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'x265_log(nullptr, X265_LOG_ERROR, "yuv: skip offset exceeds supported range\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to skip requested frames\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: skip frame payload truncated\\n" : "yuv: skip frame payload read failed\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'break;',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t frameBytes = std::fread(buf[written % QUEUE_SIZE], 1, framesize, ifs);',
                    'if (!frameBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: frame payload truncated\\n" : "yuv: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/x265cli.cpp': '\n'.join((
                    'this->input[view]->startReader();',
                    'if (this->input[view]->isFail())',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, "unable to start input reader for <%s>\\n", inputfn[view]);',
                    '    for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '    {',
                    '        if (this->input[releaseIdx])',
                    '        {',
                    '            this->input[releaseIdx]->release();',
                    '            this->input[releaseIdx] = nullptr;',
                    '        }',
                    '    }',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Y4MInput constructor must surface skip seek/read failures before leaving the reader active')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/y4m.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/y4m.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: skip offset exceeds supported range\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to skip requested frames\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame header truncated\\n" : "y4m: skip frame header read failed\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'break;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: skip frame payload truncated\\n" : "y4m: skip frame payload read failed\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'break;',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "y4m: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t headerBytes = std::fread(hbuf, 1, sizeof(hbuf), ifs);',
                    'if (!headerBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header missing\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header truncated\\n");',
                    'failed.store(true);',
                    'return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "y4m: frame payload truncated\\n" : "y4m: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/input/yuv.h': '\n'.join((
                    'std::atomic<bool> failed;',
                    'bool isFail()                                 { return failed.load() || (ifs && std::ferror(ifs)); }',
                )) + '\n',
                'source/input/yuv.cpp': '\n'.join((
                    'failed.store(true);',
                    'failed.store(!threadActive.load());',
                    'x265_log(nullptr, X265_LOG_ERROR, "yuv: skip offset exceeds supported range\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to skip requested frames\\n");',
                    'failed.store(true);',
                    'threadActive.store(false);',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: skip frame payload truncated\\n" : "yuv: skip frame payload read failed\\n");',
                    'threadActive.store(false);',
                    'break;',
                    'if (threadActive.load() && !start())',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to start reader thread\\n");',
                    '    failed.store(true);',
                    '    threadActive.store(false);',
                    '    writeCount.poke();',
                    '}',
                    'size_t frameBytes = std::fread(buf[written % QUEUE_SIZE], 1, framesize, ifs);',
                    'if (!frameBytes && std::feof(ifs))',
                    '    return false;',
                    'x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: frame payload truncated\\n" : "yuv: frame payload read failed\\n");',
                    'failed.store(true);',
                    'return false;',
                )) + '\n',
                'source/x265cli.cpp': '\n'.join((
                    'this->input[view]->startReader();',
                    'if (this->input[view]->isFail())',
                    '{',
                    '    x265_log_file(param, X265_LOG_ERROR, "unable to start input reader for <%s>\\n", inputfn[view]);',
                    '    for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)',
                    '    {',
                    '        if (this->input[releaseIdx])',
                    '        {',
                    '            this->input[releaseIdx]->release();',
                    '            this->input[releaseIdx] = nullptr;',
                    '        }',
                    '    }',
                    '    return true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'YUVInput constructor must surface skip seek/read failures before leaving the reader active')

    print('Input reader start failure guard tests passed')


if __name__ == '__main__':
    main()
