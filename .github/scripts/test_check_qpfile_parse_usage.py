#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_qpfile_parse_usage.py')

# Coverage probes used by the scan for qpfile parse guardrails.
NORMALIZED_PROBES = (
    'qpfile parsing must fail fast when ftell/fseek cannot preserve parser position',
    'missing qpfile parse guardrail: ',
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
                'source/x265cli.cpp': '\n'.join((
                    'static bool parseCliInt32Token(const char* token, int32_t& value)',
                    'static bool parseQpFileLine(char* line, int32_t& num, char& type, int32_t& qp)',
                    'static bool isQpFileSkippableLine(const char* line)',
                    'validateConfigFileLine(qpfile, "QP file", 0, line, sizeof(line))',
                    'char* frameToken = scan;',
                    'char parsedType = *scan++;',
                    'if (!parseCliInt32Token(frameToken, parsedNum))',
                    'if (!parseCliInt32Token(qpToken, parsedQp))',
                    "if (*scan == '#')",
                    'num = parsedNum;',
                    'type = parsedType;',
                    'qp = parsedQp;',
                    'filePos = std::ftell(qpfile);',
                    'if (filePos < 0)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Unable to query qpfile position before parsing frame %d\\n", pic_org.poc);',
                    'return false;',
                    'if (!std::fgets(line, sizeof(line), qpfile))',
                    'if (isQpFileSkippableLine(line))',
                    'bool hasValidLine = parseQpFileLine(line, num, type, qp);',
                    'if (num > pic_org.poc || !hasValidLine)',
                    '{',
                    'if (std::fseek(qpfile, filePos, SEEK_SET))',
                    '{',
                    'x265_log(nullptr, X265_LOG_ERROR, "Unable to restore qpfile position for frame %d\\n", pic_org.poc);',
                    'return false;',
                    '}',
                    'break;',
                    '}',
                    'if (qp < -1 || qp > QP_MAX_MAX)',
                    'int nextForceQp = 0;',
                    'int nextSliceType = X265_TYPE_AUTO;',
                    'pic_org.forceqp = nextForceQp;',
                    'pic_org.sliceType = nextSliceType;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': 'if (qp < -1 || qp > 51)\n                return 0;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden qpfile parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'static bool parseCliInt32Token(const char* token, int32_t& value)',
                    'static bool parseQpFileLine(char* line, int32_t& num, char& type, int32_t& qp)',
                    'static bool isQpFileSkippableLine(const char* line)',
                    'validateConfigFileLine(qpfile, "QP file", 0, line, sizeof(line))',
                    'char* frameToken = scan;',
                    'char parsedType = *scan++;',
                    'if (!parseCliInt32Token(frameToken, parsedNum))',
                    'if (!parseCliInt32Token(qpToken, parsedQp))',
                    "if (*scan == '#')",
                    'num = parsedNum;',
                    'type = parsedType;',
                    'qp = parsedQp;',
                    'if (filePos < 0)',
                    'x265_log(nullptr, X265_LOG_ERROR, "Unable to query qpfile position before parsing frame %d\\n", pic_org.poc);',
                    'if (!std::fgets(line, sizeof(line), qpfile))',
                    'if (isQpFileSkippableLine(line))',
                    'bool hasValidLine = parseQpFileLine(line, num, type, qp);',
                    'if (num > pic_org.poc || !hasValidLine)',
                    'std::fseek(qpfile, filePos, SEEK_SET);',
                    'if (qp < -1 || qp > QP_MAX_MAX)',
                    'int nextForceQp = 0;',
                    'int nextSliceType = X265_TYPE_AUTO;',
                    'pic_org.forceqp = nextForceQp;',
                    'pic_org.sliceType = nextSliceType;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden qpfile parse regression: std::fseek(qpfile, filePos, SEEK_SET);')

    print('QPFile parse guard tests passed')


if __name__ == '__main__':
    main()
