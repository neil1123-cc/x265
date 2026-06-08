#!/usr/bin/env python3
import argparse
from pathlib import Path


API_TARGET = Path('source/encoder/api.cpp')
ENCODER_TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_API_SNIPPETS = (
    'if (encoder && encoder->m_param)',
    'encoder->stopJobs();',
    'encoder->destroy();',
    'else',
    'PARAM_NS::x265_param_free(param);',
    'PARAM_NS::x265_param_free(latestParam);',
    'PARAM_NS::x265_param_free(zoneParam);',
    'delete encoder;',
)
REQUIRED_ENCODER_SNIPPETS = (
    'm_numPools = 0;',
    'm_bToneMap = 0;',
    'm_enableNal = 0;',
    'm_variance = nullptr;',
    'm_rdCost = nullptr;',
    'm_trainingCount = nullptr;',
    'zoneReadCount = nullptr;',
    'zoneWriteCount = nullptr;',
    'm_dupPicOne[i] = nullptr;',
    'm_dupPicTwo[i] = nullptr;',
    'if (m_dupBuffer[i])',
    'if (m_dupBuffer[i]->dupPic)',
    'clearDupPictureSideData(m_dupBuffer[i]->dupPic);',
    'x265_picture_free(m_dupBuffer[i]->dupPic);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    api_path = repo_root / API_TARGET
    if not api_path.is_file():
        failures.append((API_TARGET.as_posix(), 0, 'missing file'))
    else:
        api_text = api_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in REQUIRED_API_SNIPPETS:
            if snippet not in api_text:
                failures.append((API_TARGET.as_posix(), 0, f'missing encoder-open fail cleanup guardrail: {snippet}'))

        fail_pos = api_text.find('fail:')
        cleanup_guard_pos = api_text.find('if (encoder && encoder->m_param)', fail_pos if fail_pos != -1 else 0)
        stop_pos = api_text.find('encoder->stopJobs();', cleanup_guard_pos if cleanup_guard_pos != -1 else 0)
        destroy_pos = api_text.find('encoder->destroy();', stop_pos if stop_pos != -1 else 0)
        free_pos = api_text.find('PARAM_NS::x265_param_free(param);', destroy_pos if destroy_pos != -1 else 0)
        delete_pos = api_text.find('delete encoder;', free_pos if free_pos != -1 else 0)
        if -1 in (fail_pos, cleanup_guard_pos, stop_pos, destroy_pos, free_pos, delete_pos) or not (
            fail_pos < cleanup_guard_pos < stop_pos < destroy_pos < free_pos < delete_pos
        ):
            failures.append((API_TARGET.as_posix(), 0, 'x265_encoder_open must stop jobs and destroy a partially initialized encoder before falling back to manual param frees'))

    encoder_path = repo_root / ENCODER_TARGET
    if not encoder_path.is_file():
        failures.append((ENCODER_TARGET.as_posix(), 0, 'missing file'))
    else:
        encoder_text = encoder_path.read_text(encoding='utf-8', errors='ignore')
        for snippet in REQUIRED_ENCODER_SNIPPETS:
            if snippet not in encoder_text:
                failures.append((ENCODER_TARGET.as_posix(), 0, f'missing encoder partial-destroy guardrail: {snippet}'))

        ctor_pos = encoder_text.find('Encoder::Encoder()')
        init_num_pools_pos = encoder_text.find('m_numPools = 0;', ctor_pos if ctor_pos != -1 else 0)
        init_zone_pos = encoder_text.find('zoneReadCount = nullptr;', init_num_pools_pos if init_num_pools_pos != -1 else 0)
        init_dup_pos = encoder_text.find('m_dupPicOne[i] = nullptr;', init_zone_pos if init_zone_pos != -1 else 0)
        destroy_pos = encoder_text.find('void Encoder::destroy()')
        dup_guard_pos = encoder_text.find('if (m_dupBuffer[i])', destroy_pos if destroy_pos != -1 else 0)
        pic_guard_pos = encoder_text.find('if (m_dupBuffer[i]->dupPic)', dup_guard_pos if dup_guard_pos != -1 else 0)
        free_pic_pos = encoder_text.find('x265_picture_free(m_dupBuffer[i]->dupPic);', pic_guard_pos if pic_guard_pos != -1 else 0)
        if -1 in (ctor_pos, init_num_pools_pos, init_zone_pos, init_dup_pos, destroy_pos, dup_guard_pos, pic_guard_pos, free_pic_pos) or not (
            ctor_pos < init_num_pools_pos < init_zone_pos < init_dup_pos and destroy_pos < dup_guard_pos < pic_guard_pos < free_pic_pos
        ):
            failures.append((ENCODER_TARGET.as_posix(), 0, 'Encoder ctor and destroy must initialize and guard partial frame-duplication state for open-failure cleanup'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check encoder-open failure cleanup guardrails')
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

    print('Encoder-open failure cleanup validated')


if __name__ == '__main__':
    main()
