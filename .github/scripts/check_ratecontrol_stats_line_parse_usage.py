#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/ratecontrol.cpp')
FORBIDDEN_SNIPPETS = (
    'sscanf(p, " in:%*d out:%*d type:%c q:%lf q-aq:%lf q-noVbv:%lf q-Rceq:%lf tex:%d mv:%d misc:%d icu:%lf pcu:%lf scu:%lf sc:%d",',
    'sscanf(p, " in:%*d out:%*d type:%c q:%lf q-aq:%lf q-noVbv:%lf q-Rceq:%lf tex:%d mv:%d misc:%d icu:%lf pcu:%lf scu:%lf nump:%d numnegp:%d numposp:%d deltapoc:%127s bused:%39s",',
    'if (e < 10)',
    'splitdeltaPOC(deltaPOC, rce);',
    'splitbUsed(bUsed, rce);',
)
HELPER_REQUIRED_SNIPPETS = (
    'static bool validateStatsRpsCounts(int numberOfPictures, int numberOfNegativePictures, int numberOfPositivePictures)',
    'static bool parseStatsLineFields(const char* p, char& picType, double& qpRc, double& qpAq, double& qNoVbv,',
    'static bool parseStatsLineDoubleValue(const char*& cursor, const char* label, double& value)',
    'static bool parseStatsLineTokenValue(const char*& cursor, const char* label, char* value, size_t valueSize)',
    '&& validateStatsRpsCounts(numberOfPictures, numberOfNegativePictures, numberOfPositivePictures)',
    'char token[64];',
    'if (!parseRateControlDoubleToken(token, value))',
)
CALLER_REQUIRED_SNIPPETS = (
    'if (!m_param->bMultiPassOptRPS)',
    'int scenecut = 0;',
    'e = parseStatsLineFields(p + consumedPrefix, picType, qpRc, qpAq, qNoVbv, qRceq,',
    'rcePocOrder->scenecut = scenecut != 0;',
    'char deltaPOC[128] = {};',
    'char bUsed[40] = {};',
    'rce->rpsIdx = -1;',
    '&& splitdeltaPOC(deltaPOC, rce)',
    '&& splitbUsed(bUsed, rce) ? 18 : -1;',
    'if ((!m_param->bMultiPassOptRPS && e != 14) || (m_param->bMultiPassOptRPS && e != 18))',
)
SPLIT_DELTA_REQUIRED_SNIPPETS = (
    'bool RateControl::splitdeltaPOC(const char deltapoc[], RateControlEntry *rce)',
    'if (idx >= rce->rpsData.numberOfPictures)',
    'if (idx != rce->rpsData.numberOfPictures)',
    'if (!parseRateControlIntToken(tmpStr, deltaPOC))',
)
SPLIT_BUSED_REQUIRED_SNIPPETS = (
    'bool RateControl::splitbUsed(const char bused[], RateControlEntry *rce)',
    'if (idx >= rce->rpsData.numberOfPictures)',
    'if (idx != rce->rpsData.numberOfPictures)',
    'if (!parseRateControlIntToken(tmpStr, bUsed) || bUsed < 0 || bUsed > 1)',
)
HELPER_REGION_START = 'static bool validateStatsRpsCounts(int numberOfPictures, int numberOfNegativePictures, int numberOfPositivePictures)'
HELPER_REGION_END = 'inline int calcScale(uint64_t x)'
CALLER_REGION_START = 'if (!m_param->bMultiPassOptRPS)'
CALLER_REGION_END = 'if ((!m_param->bMultiPassOptRPS && e != 14) || (m_param->bMultiPassOptRPS && e != 18))'
SPLIT_DELTA_REGION_START = 'bool RateControl::splitdeltaPOC(const char deltapoc[], RateControlEntry *rce)'
SPLIT_DELTA_REGION_END = 'bool RateControl::splitbUsed(const char bused[], RateControlEntry *rce)'
SPLIT_BUSED_REGION_START = 'bool RateControl::splitbUsed(const char bused[], RateControlEntry *rce)'
SPLIT_BUSED_REGION_END = 'double RateControl::forwardMasking(Frame* curFrame, double q)'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    end += len(end_marker)
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    helper_region = get_region(text, HELPER_REGION_START, HELPER_REGION_END)
    caller_region = get_region(text, CALLER_REGION_START, CALLER_REGION_END)
    split_delta_region = get_region(text, SPLIT_DELTA_REGION_START, SPLIT_DELTA_REGION_END)
    split_bused_region = get_region(text, SPLIT_BUSED_REGION_START, SPLIT_BUSED_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ratecontrol stats-line parse regression: {snippet}'))
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol stats-line parse guardrail: {snippet}'))
    for snippet in CALLER_REQUIRED_SNIPPETS:
        if snippet not in caller_region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol stats-line parse guardrail: {snippet}'))
    for snippet in SPLIT_DELTA_REQUIRED_SNIPPETS:
        if snippet not in split_delta_region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol stats-line parse guardrail: {snippet}'))
    for snippet in SPLIT_BUSED_REQUIRED_SNIPPETS:
        if snippet not in split_bused_region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol stats-line parse guardrail: {snippet}'))
    if all(snippet in helper_region for snippet in HELPER_REQUIRED_SNIPPETS):
        if not has_in_order(
            helper_region,
            (
                'static bool validateStatsRpsCounts(int numberOfPictures, int numberOfNegativePictures, int numberOfPositivePictures)',
                'static bool parseStatsLineDoubleValue(const char*& cursor, const char* label, double& value)',
                'char token[64];',
                'if (!parseRateControlDoubleToken(token, value))',
                'static bool parseStatsLineTokenValue(const char*& cursor, const char* label, char* value, size_t valueSize)',
                'static bool parseStatsLineFields(const char* p, char& picType, double& qpRc, double& qpAq, double& qNoVbv,',
                '&& parseStatsLineIntValue(cursor, " sc:", scenecut)',
                'static bool parseStatsLineFields(const char* p, char& picType, double& qpRc, double& qpAq, double& qNoVbv,',
                '&& parseStatsLineIntValue(cursor, " numposp:", numberOfPositivePictures)',
                '&& validateStatsRpsCounts(numberOfPictures, numberOfNegativePictures, numberOfPositivePictures)',
                '&& parseStatsLineTokenValue(cursor, " deltapoc:", deltaPOC, deltaPOCSize)',
                '&& parseStatsLineTokenValue(cursor, " bused:", bUsed, bUsedSize)',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseStatsLineFields must validate scalar fields, RPS counts, and deltapoc/bused token extraction in order before accepting a stats line'))
    if all(snippet in caller_region for snippet in CALLER_REQUIRED_SNIPPETS):
        if not has_in_order(
            caller_region,
            (
                'if (!m_param->bMultiPassOptRPS)',
                'int scenecut = 0;',
                'e = parseStatsLineFields(p + consumedPrefix, picType, qpRc, qpAq, qNoVbv, qRceq,',
                'rcePocOrder->scenecut = scenecut != 0;',
                'char deltaPOC[128] = {};',
                'char bUsed[40] = {};',
                'rce->rpsData.numberOfPictures,',
                'deltaPOC, sizeof(deltaPOC), bUsed, sizeof(bUsed))',
                '&& splitdeltaPOC(deltaPOC, rce)',
                '&& splitbUsed(bUsed, rce) ? 18 : -1;',
                'rce->rpsIdx = -1;',
                'if ((!m_param->bMultiPassOptRPS && e != 14) || (m_param->bMultiPassOptRPS && e != 18))',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'stats-file loading must finish parseStatsLineFields and RPS token splitting before accepting an 18-field RPS entry'))
    if all(snippet in split_delta_region for snippet in SPLIT_DELTA_REQUIRED_SNIPPETS):
        if not has_in_order(
            split_delta_region,
            (
                'bool RateControl::splitdeltaPOC(const char deltapoc[], RateControlEntry *rce)',
                'if (idx >= rce->rpsData.numberOfPictures)',
                'if (!parseRateControlIntToken(tmpStr, deltaPOC))',
                'rce->rpsData.deltaPOC[idx] = deltaPOC;',
                'idx++;',
                'if (idx != rce->rpsData.numberOfPictures)',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'splitdeltaPOC must bounds-check and parse each RPS entry before storing it, then verify the final picture count'))
    if all(snippet in split_bused_region for snippet in SPLIT_BUSED_REQUIRED_SNIPPETS):
        if not has_in_order(
            split_bused_region,
            (
                'bool RateControl::splitbUsed(const char bused[], RateControlEntry *rce)',
                'if (idx >= rce->rpsData.numberOfPictures)',
                'if (!parseRateControlIntToken(tmpStr, bUsed) || bUsed < 0 || bUsed > 1)',
                'rce->rpsData.bUsed[idx] = bUsed > 0;',
                'idx++;',
                'if (idx != rce->rpsData.numberOfPictures)',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'splitbUsed must bounds-check and validate each RPS flag before storing it, then verify the final picture count'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed ratecontrol stats-line parsing guardrails')
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

    print('Ratecontrol stats-line parse usage validated')


if __name__ == '__main__':
    main()
