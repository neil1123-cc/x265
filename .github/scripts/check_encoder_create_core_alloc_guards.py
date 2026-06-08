#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    required = (
        'm_lookahead = new (std::nothrow) Lookahead(m_param, lookAheadThreadPool);',
        'if (!m_lookahead)',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead instance, aborting\\n");',
        'm_dpb = new (std::nothrow) DPB(m_param);',
        'if (!m_dpb)',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate DPB instance, aborting\\n");',
        'm_rateControl = new (std::nothrow) RateControl(*m_param, this);',
        'if (!m_rateControl)',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate rate-control instance, aborting\\n");',
        'zoneReadCount = new (std::nothrow) ThreadSafeInteger[m_param->rc.zonefileCount];',
        'if (!zoneReadCount)',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate zone-read counters, aborting\\n");',
        'zoneWriteCount = new (std::nothrow) ThreadSafeInteger[m_param->rc.zonefileCount];',
        'if (!zoneWriteCount)',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate zone-write counters, aborting\\n");',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing encoder create core alloc guardrail: {snippet}'))

    forbidden = (
        'm_lookahead = new Lookahead(m_param, lookAheadThreadPool);',
        'm_dpb = new DPB(m_param);',
        'm_rateControl = new RateControl(*m_param, this);',
        'zoneReadCount = new ThreadSafeInteger[m_param->rc.zonefileCount];',
        'zoneWriteCount = new ThreadSafeInteger[m_param->rc.zonefileCount];',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden encoder create core alloc regression: {snippet}'))

    lookahead_alloc_pos = text.find('m_lookahead = new (std::nothrow) Lookahead(m_param, lookAheadThreadPool);')
    lookahead_guard_pos = text.find('if (!m_lookahead)', lookahead_alloc_pos if lookahead_alloc_pos != -1 else 0)
    lookahead_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead instance, aborting\\n");', lookahead_guard_pos if lookahead_guard_pos != -1 else 0)
    dpb_alloc_pos = text.find('m_dpb = new (std::nothrow) DPB(m_param);', lookahead_log_pos if lookahead_log_pos != -1 else 0)
    dpb_guard_pos = text.find('if (!m_dpb)', dpb_alloc_pos if dpb_alloc_pos != -1 else 0)
    dpb_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate DPB instance, aborting\\n");', dpb_guard_pos if dpb_guard_pos != -1 else 0)
    rate_alloc_pos = text.find('m_rateControl = new (std::nothrow) RateControl(*m_param, this);', dpb_log_pos if dpb_log_pos != -1 else 0)
    rate_guard_pos = text.find('if (!m_rateControl)', rate_alloc_pos if rate_alloc_pos != -1 else 0)
    rate_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate rate-control instance, aborting\\n");', rate_guard_pos if rate_guard_pos != -1 else 0)
    zone_read_alloc_pos = text.find('zoneReadCount = new (std::nothrow) ThreadSafeInteger[m_param->rc.zonefileCount];', rate_log_pos if rate_log_pos != -1 else 0)
    zone_read_guard_pos = text.find('if (!zoneReadCount)', zone_read_alloc_pos if zone_read_alloc_pos != -1 else 0)
    zone_read_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate zone-read counters, aborting\\n");', zone_read_guard_pos if zone_read_guard_pos != -1 else 0)
    zone_write_alloc_pos = text.find('zoneWriteCount = new (std::nothrow) ThreadSafeInteger[m_param->rc.zonefileCount];', zone_read_log_pos if zone_read_log_pos != -1 else 0)
    zone_write_guard_pos = text.find('if (!zoneWriteCount)', zone_write_alloc_pos if zone_write_alloc_pos != -1 else 0)
    zone_write_log_pos = text.find('x265_log(m_param, X265_LOG_ERROR, "Unable to allocate zone-write counters, aborting\\n");', zone_write_guard_pos if zone_write_guard_pos != -1 else 0)
    if -1 in (
        lookahead_alloc_pos, lookahead_guard_pos, lookahead_log_pos,
        dpb_alloc_pos, dpb_guard_pos, dpb_log_pos,
        rate_alloc_pos, rate_guard_pos, rate_log_pos,
        zone_read_alloc_pos, zone_read_guard_pos, zone_read_log_pos,
        zone_write_alloc_pos, zone_write_guard_pos, zone_write_log_pos,
    ) or not (
        lookahead_alloc_pos < lookahead_guard_pos < lookahead_log_pos <
        dpb_alloc_pos < dpb_guard_pos < dpb_log_pos <
        rate_alloc_pos < rate_guard_pos < rate_log_pos <
        zone_read_alloc_pos < zone_read_guard_pos < zone_read_log_pos <
        zone_write_alloc_pos < zone_write_guard_pos < zone_write_log_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Encoder::create must reject Lookahead, DPB, RateControl, and zone counter allocation failures before use'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Encoder::create core allocation guards')
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

    print('Encoder::create core allocation guards validated')


if __name__ == '__main__':
    main()
