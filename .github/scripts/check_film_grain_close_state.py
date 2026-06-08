#!/usr/bin/env python3
import argparse
from pathlib import Path


FRAME_TARGET = Path('source/encoder/frameencoder.cpp')
ENCODER_TARGET = Path('source/encoder/encoder.cpp')
FORBIDDEN_SNIPPETS = (
    'ferror(this->m_top->m_filmGrainIn) || fclose(this->m_top->m_filmGrainIn)',
    'ferror(this->m_top->m_aomFilmGrainIn) || fclose(this->m_top->m_aomFilmGrainIn)',
    'std::ferror(m_filmGrainIn) || std::fclose(m_filmGrainIn)',
    'std::ferror(m_aomFilmGrainIn) || std::fclose(m_aomFilmGrainIn)',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = ferror(this->m_top->m_filmGrainIn) != 0;',
    'if (fclose(this->m_top->m_filmGrainIn))',
    'x265_log(this->m_param, X265_LOG_WARNING, "Unable to close film grain model file after parse failure\\n");',
    'this->m_top->m_filmGrainIn = nullptr;',
    'bool closeFailed = ferror(this->m_top->m_aomFilmGrainIn) != 0;',
    'if (fclose(this->m_top->m_aomFilmGrainIn))',
    'x265_log(this->m_param, X265_LOG_WARNING, "Unable to close AOM film grain model file after parse failure\\n");',
    'this->m_top->m_aomFilmGrainIn = nullptr;',
    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
    'if (std::fclose(m_filmGrainIn))',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close film grain file \\"%s\\" after open failure\\n", m_param->filmGrain);',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close film grain file \\"%s\\"\\n", m_param->filmGrain);',
    'm_filmGrainIn = nullptr;',
    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
    'if (std::fclose(m_aomFilmGrainIn))',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\" after open failure\\n", m_param->aomFilmGrain);',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\"\\n", m_param->aomFilmGrain);',
    'm_aomFilmGrainIn = nullptr;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    frame_path = repo_root / FRAME_TARGET
    encoder_path = repo_root / ENCODER_TARGET
    failures = []
    if not frame_path.is_file():
        failures.append((FRAME_TARGET.as_posix(), 0, 'missing file'))
        return failures
    if not encoder_path.is_file():
        failures.append((ENCODER_TARGET.as_posix(), 0, 'missing file'))
        return failures

    frame_text = frame_path.read_text(encoding='utf-8', errors='ignore')
    encoder_text = encoder_path.read_text(encoding='utf-8', errors='ignore')
    frame_start = frame_text.find('/* Write Film grain characteristics if present */')
    frame_end = frame_text.find('/* Write user SEI */', frame_start)
    frame_region = frame_text[frame_start:frame_end] if -1 not in (frame_start, frame_end) else frame_text
    open_start = encoder_text.find('if (m_param->filmGrain)')
    open_end = encoder_text.find('m_bZeroLatency =', open_start)
    open_region = encoder_text[open_start:open_end] if -1 not in (open_start, open_end) else encoder_text
    destroy_start = encoder_text.find('if (m_filmGrainIn)')
    destroy_end = encoder_text.find('#ifdef SVT_HEVC', destroy_start)
    destroy_region = encoder_text[destroy_start:destroy_end] if -1 not in (destroy_start, destroy_end) else encoder_text
    combined = frame_region + open_region + destroy_region

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in combined:
            failures.append((FRAME_TARGET.as_posix(), 0, f'missing film grain close guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in combined:
            failures.append((FRAME_TARGET.as_posix(), 0, f'forbidden film grain short-circuit close regression: {snippet}'))

    if frame_region.count('if (fclose(this->m_top->m_filmGrainIn))') != 1 or frame_region.count('if (fclose(this->m_top->m_aomFilmGrainIn))') != 1:
        failures.append((FRAME_TARGET.as_posix(), 0, 'expected one guarded parse-failure close path for each film grain model in frameencoder'))
    if open_region.count('if (std::fclose(m_filmGrainIn))') != 1 or open_region.count('if (std::fclose(m_aomFilmGrainIn))') != 1:
        failures.append((ENCODER_TARGET.as_posix(), 0, 'expected one guarded open-failure close path for each film grain file in encoder startup'))
    if destroy_region.count('if (std::fclose(m_filmGrainIn))') != 1 or destroy_region.count('if (std::fclose(m_aomFilmGrainIn))') != 1:
        failures.append((ENCODER_TARGET.as_posix(), 0, 'expected one guarded destroy close path for each film grain file in encoder teardown'))

    frame_fg_close = frame_region.find('bool closeFailed = ferror(this->m_top->m_filmGrainIn) != 0;')
    frame_fg_warn = frame_region.find('x265_log(this->m_param, X265_LOG_WARNING, "Unable to close film grain model file after parse failure\\n");')
    frame_fg_null = frame_region.find('this->m_top->m_filmGrainIn = nullptr;')
    frame_aom_close = frame_region.find('bool closeFailed = ferror(this->m_top->m_aomFilmGrainIn) != 0;')
    frame_aom_warn = frame_region.find('x265_log(this->m_param, X265_LOG_WARNING, "Unable to close AOM film grain model file after parse failure\\n");')
    frame_aom_null = frame_region.find('this->m_top->m_aomFilmGrainIn = nullptr;')
    if -1 not in (frame_fg_close, frame_fg_warn, frame_fg_null, frame_aom_close, frame_aom_warn, frame_aom_null):
        if not (frame_fg_close < frame_fg_warn < frame_fg_null < frame_aom_close < frame_aom_warn < frame_aom_null):
            failures.append((FRAME_TARGET.as_posix(), 0, 'frameencoder film grain close guards must preserve parse-failure warning and null-reset ordering'))

    open_fg_close = open_region.find('bool closeFailed = std::ferror(m_filmGrainIn) != 0;')
    open_fg_warn = open_region.find('x265_log_file(nullptr, X265_LOG_WARNING, "failed to close film grain file \\"%s\\" after open failure\\n", m_param->filmGrain);')
    open_fg_null = open_region.find('m_filmGrainIn = nullptr;', open_fg_warn)
    open_aom_close = open_region.find('bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;')
    open_aom_warn = open_region.find('x265_log_file(nullptr, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\" after open failure\\n", m_param->aomFilmGrain);')
    open_aom_null = open_region.find('m_aomFilmGrainIn = nullptr;', open_aom_warn)
    if -1 not in (open_fg_close, open_fg_warn, open_fg_null, open_aom_close, open_aom_warn, open_aom_null):
        if not (open_fg_close < open_fg_warn < open_fg_null < open_aom_close < open_aom_warn < open_aom_null):
            failures.append((ENCODER_TARGET.as_posix(), 0, 'encoder startup must preserve film grain open-failure close ordering and null resets'))

    destroy_fg_close = destroy_region.find('bool closeFailed = std::ferror(m_filmGrainIn) != 0;')
    destroy_fg_warn = destroy_region.find('x265_log_file(m_param, X265_LOG_WARNING, "failed to close film grain file \\"%s\\"\\n", m_param->filmGrain);')
    destroy_fg_null = destroy_region.find('m_filmGrainIn = nullptr;', destroy_fg_warn)
    destroy_aom_close = destroy_region.find('bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;')
    destroy_aom_warn = destroy_region.find('x265_log_file(m_param, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\"\\n", m_param->aomFilmGrain);')
    destroy_aom_null = destroy_region.find('m_aomFilmGrainIn = nullptr;', destroy_aom_warn)
    if -1 not in (destroy_fg_close, destroy_fg_warn, destroy_fg_null, destroy_aom_close, destroy_aom_warn, destroy_aom_null):
        if not (destroy_fg_close < destroy_fg_warn < destroy_fg_null < destroy_aom_close < destroy_aom_warn < destroy_aom_null):
            failures.append((ENCODER_TARGET.as_posix(), 0, 'encoder teardown must preserve film grain close ordering and null resets'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check film grain close state')
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

    print('Film grain close guard validated')


if __name__ == '__main__':
    main()
