#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'void CLIOptions::printStatus(uint32_t frameNum)',
    'uint32_t progressFrames = (param->chunkEnd ? param->chunkEnd : param->totalFrames);',
    'percentage = progressFrames ? 100. * frameNum / progressFrames : 0.;',
    '"x265 [%.1f%%] %d/%d frames, %.*f fps, %.*f kb/s, %.*f %sB, eta %d:%02d:%02d, est.size %.*f %sB"',
    '"\\rx265 [%5.1f%%] %d/%d %.*f fps %.*f kb/s eta %d:%02d:%02d   "',
    '"{\\"frame\\":%u,\\"frames\\":%u,\\"fps\\":%.*f,\\"bitrate\\":%.*f,\\"size_bytes\\":%.0f,\\"progress\\":%.4f,\\"eta_seconds\\":%d}\\n"',
)
FORBIDDEN_SNIPPETS = (
    'percentage = 100. * frameNum / (param->chunkEnd ? param->chunkEnd : param->totalFrames);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    function_start = text.find('void CLIOptions::printStatus(uint32_t frameNum)')
    function_end = text.find('bool CLIOptions::parse(', function_start if function_start != -1 else 0)
    function_text = text[function_start:function_end] if -1 not in (function_start, function_end) else text
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in function_text:
            failures.append((TARGET.as_posix(), 0, f'missing printStatus progress guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in function_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden printStatus progress regression: {snippet}'))

    progress_pos = function_text.find('uint32_t progressFrames = (param->chunkEnd ? param->chunkEnd : param->totalFrames);')
    percent_pos = function_text.find('percentage = progressFrames ? 100. * frameNum / progressFrames : 0.;', progress_pos)
    summary_call_pos = function_text.find('"x265 [%.1f%%] %d/%d frames, %.*f fps, %.*f kb/s, %.*f %sB, eta %d:%02d:%02d, est.size %.*f %sB"', percent_pos)
    summary_use_pos = function_text.find('percentage, frameNum, progressFrames,', summary_call_pos)
    stylish_call_pos = function_text.find('"\\rx265 [%5.1f%%] %d/%d %.*f fps %.*f kb/s eta %d:%02d:%02d   "', summary_use_pos)
    stylish_use_pos = function_text.find('percentage, frameNum, progressFrames,', stylish_call_pos)
    file_call_pos = function_text.find('"{\\"frame\\":%u,\\"frames\\":%u,\\"fps\\":%.*f,\\"bitrate\\":%.*f,\\"size_bytes\\":%.0f,\\"progress\\":%.4f,\\"eta_seconds\\":%d}\\n"', stylish_use_pos)
    file_use_pos = function_text.find('frameNum, progressFrames, fps_prec, fps, bitrate_prec, bitrate,', file_call_pos)
    if -1 in (progress_pos, percent_pos) or not (progress_pos < percent_pos):
        failures.append((TARGET.as_posix(), 0, 'printStatus must guard zero progress frame targets before computing percentage'))
    if -1 in (summary_call_pos, summary_use_pos) or not (summary_call_pos < summary_use_pos):
        failures.append((TARGET.as_posix(), 0, 'printStatus summary output must use guarded progress frame totals'))
    if -1 in (stylish_call_pos, stylish_use_pos) or not (stylish_call_pos < stylish_use_pos):
        failures.append((TARGET.as_posix(), 0, 'printStatus stylish output must use guarded progress frame totals'))
    if -1 in (file_call_pos, file_use_pos) or not (file_call_pos < file_use_pos):
        failures.append((TARGET.as_posix(), 0, 'printStatus progress file output must use guarded progress frame totals'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check printStatus progress guard')
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

    print('printStatus progress guard validated')


if __name__ == '__main__':
    main()
