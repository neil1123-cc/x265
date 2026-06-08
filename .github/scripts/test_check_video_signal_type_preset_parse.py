#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_video_signal_type_preset_parse.py')

# Coverage probes used by the scan for video-signal-type-preset parse guardrails.
NORMALIZED_PROBES = (
    'forbidden video-signal-type-preset parse regression: ',
    'missing video-signal-type-preset parse guardrail: ',
    'video-signal-type-preset parsing must copy bounded tokens before validating optional colon-separated components',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'static bool copyVideoSignalTypeToken(const char* start, size_t length, char (&out)[20])',
                    'if (!start || !length || length >= sizeof(out))',
                    'std::memcpy(out, start, length);',
                    "out[length] = '\\0';",
                    'static bool parseVideoSignalTypePresetTokens(const char* preset, char (&systemId)[20], char (&colorVolume)[20])',
                    "const char* separator = std::strchr(preset, ':');",
                    'return copyVideoSignalTypeToken(preset, std::strlen(preset), systemId);',
                    'if (!systemIdLength || !colorVolumeLength)',
                    'using namespace X265_NS;',
                    'void Encoder::configureVideoSignalTypePreset(x265_param* p)',
                    'char systemId[20] = {};',
                    'char colorVolume[20] = {};',
                    'if (!parseVideoSignalTypePresetTokens(p->videoSignalTypePreset, systemId, colorVolume))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Incorrect video-signal-type-preset, aborting\\n");',
                    'm_aborted = true;',
                    'return;',
                    'uint32_t sysId = 0;',
                    'while (std::strcmp(vstPresets[sysId].systemId, systemId))',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': 'int parsed = std::sscanf(p->videoSignalTypePreset, "%19[^:]:%19[^:]%n", systemId, colorVolume, &consumed);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden video-signal-type-preset parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'static bool copyVideoSignalTypeToken(const char* start, size_t length, char (&out)[20])',
                    'if (!start || !length || length >= sizeof(out))',
                    'std::memcpy(out, start, length);',
                    "out[length] = '\\0';",
                    'static bool parseVideoSignalTypePresetTokens(const char* preset, char (&systemId)[20], char (&colorVolume)[20])',
                    "const char* separator = std::strchr(preset, ':');",
                    'return copyVideoSignalTypeToken(preset, std::strlen(preset), systemId);',
                    'if (!systemIdLength || !colorVolumeLength)',
                    'using namespace X265_NS;',
                    'void Encoder::configureVideoSignalTypePreset(x265_param* p)',
                    'char systemId[20] = {};',
                    'char colorVolume[20] = {};',
                    'uint32_t sysId = 0;',
                    'if (!parseVideoSignalTypePresetTokens(p->videoSignalTypePreset, systemId, colorVolume))',
                    'x265_log(nullptr, X265_LOG_ERROR, "Incorrect video-signal-type-preset, aborting\\n");',
                    'm_aborted = true;',
                    'return;',
                    'while (std::strcmp(vstPresets[sysId].systemId, systemId))',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'configureVideoSignalTypePreset must reject malformed preset tokens before initializing the preset lookup state')

    print('Video signal type preset parse guard tests passed')


if __name__ == '__main__':
    main()
