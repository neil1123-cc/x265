#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_print_status_progress_guard.py')

# Coverage probes used by the scan for printStatus progress guardrails.
NORMALIZED_PROBES = (
    'printStatus must guard zero progress frame targets before computing percentage',
    'printStatus summary output must use guarded progress frame totals',
    'printStatus stylish output must use guarded progress frame totals',
    'missing printStatus progress guardrail: ',
    'forbidden printStatus progress regression: ',
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
                    'void CLIOptions::printStatus(uint32_t frameNum)',
                    '{',
                    'uint32_t progressFrames = (param->chunkEnd ? param->chunkEnd : param->totalFrames);',
                    'percentage = progressFrames ? 100. * frameNum / progressFrames : 0.;',
                    'std::snprintf(buf, sizeof(buf), "x265 [%.1f%%] %d/%d frames, %.*f fps, %.*f kb/s, %.*f %sB, eta %d:%02d:%02d, est.size %.*f %sB",',
                    '    percentage, frameNum, progressFrames, fps_prec, fps, bitrate_prec, bitrate,',
                    '    file_prec, file_num, file_unit,',
                    '    eta_hh, eta_mm, eta_ss,',
                    '    estsz_prec, estsz_num, estsz_unit);',
                    'std::fprintf(stderr, "\\rx265 [%5.1f%%] %d/%d %.*f fps %.*f kb/s eta %d:%02d:%02d   ",',
                    '    percentage, frameNum, progressFrames, fps_prec, fps, bitrate_prec, bitrate,',
                    '    eta_hh, eta_mm, eta_ss);',
                    'bool wroteProgress = std::fprintf(progressfp,',
                    '    "{\\"frame\\":%u,\\"frames\\":%u,\\"fps\\":%.*f,\\"bitrate\\":%.*f,\\"size_bytes\\":%.0f,\\"progress\\":%.4f,\\"eta_seconds\\":%d}\\n",',
                    '    frameNum, progressFrames, fps_prec, fps, bitrate_prec, bitrate,',
                    '    (double)totalbytes, framesToBeEncoded ? percentage / 100.0 : 0.0, framesToBeEncoded ? eta : 0) >= 0;',
                    '}',
                    'bool CLIOptions::parse(int argc, char **argv, x265_param *param)',
                    '{',
                    '    return false;',
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
                'source/x265cli.cpp': '\n'.join((
                    'void CLIOptions::printStatus(uint32_t frameNum)',
                    '{',
                    'percentage = 100. * frameNum / (param->chunkEnd ? param->chunkEnd : param->totalFrames);',
                    '}',
                    'bool CLIOptions::parse(int argc, char **argv, x265_param *param)',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden printStatus progress regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/x265cli.cpp': '\n'.join((
                    'void CLIOptions::printStatus(uint32_t frameNum)',
                    '{',
                    'uint32_t progressFrames = (param->chunkEnd ? param->chunkEnd : param->totalFrames);',
                    'percentage = progressFrames ? 100. * frameNum / progressFrames : 0.;',
                    'std::snprintf(buf, sizeof(buf), "x265 [%.1f%%] %d/%d frames, %.*f fps, %.*f kb/s, %.*f %sB, eta %d:%02d:%02d, est.size %.*f %sB",',
                    '    percentage, frameNum, progressFrames, fps_prec, fps, bitrate_prec, bitrate,',
                    '    file_prec, file_num, file_unit,',
                    '    eta_hh, eta_mm, eta_ss,',
                    '    estsz_prec, estsz_num, estsz_unit);',
                    'std::fprintf(stderr, "\\rx265 [%5.1f%%] %d/%d %.*f fps %.*f kb/s eta %d:%02d:%02d   ",',
                    '    percentage, frameNum, progressFrames, fps_prec, fps, bitrate_prec, bitrate,',
                    '    eta_hh, eta_mm, eta_ss);',
                    'bool wroteProgress = std::fprintf(progressfp,',
                    '    "{\\"frame\\":%u,\\"frames\\":%u,\\"fps\\":%.*f,\\"bitrate\\":%.*f,\\"size_bytes\\":%.0f,\\"progress\\":%.4f,\\"eta_seconds\\":%d}\\n",',
                    '    frameNum, totalFrames, fps_prec, fps, bitrate_prec, bitrate,',
                    '    (double)totalbytes, framesToBeEncoded ? percentage / 100.0 : 0.0, framesToBeEncoded ? eta : 0) >= 0;',
                    '}',
                    'bool CLIOptions::parse(int argc, char **argv, x265_param *param)',
                    '{',
                    '    return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'printStatus progress file output must use guarded progress frame totals')

    print('printStatus progress guard tests passed')


if __name__ == '__main__':
    main()
