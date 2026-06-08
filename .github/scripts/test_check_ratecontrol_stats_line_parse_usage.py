#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_stats_line_parse_usage.py')

# Coverage probes used by the scan for ratecontrol stats-line parsing guardrails.
NORMALIZED_PROBES = (
    'forbidden ratecontrol stats-line parse regression: ',
    'missing ratecontrol stats-line parse guardrail: ',
    'parseStatsLineFields must validate scalar fields, RPS counts, and deltapoc/bused token extraction in order before accepting a stats line',
    'splitdeltaPOC must bounds-check and parse each RPS entry before storing it, then verify the final picture count',
    'splitbUsed must bounds-check and validate each RPS flag before storing it, then verify the final picture count',
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
                'source/encoder/ratecontrol.cpp': '\n'.join((
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
                    'inline int calcScale(uint64_t x)',
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
                    'bool RateControl::splitdeltaPOC(const char deltapoc[], RateControlEntry *rce)',
                    'if (idx >= rce->rpsData.numberOfPictures)',
                    'if (!parseRateControlIntToken(tmpStr, deltaPOC))',
                    'rce->rpsData.deltaPOC[idx] = deltaPOC;',
                    'idx++;',
                    'if (idx != rce->rpsData.numberOfPictures)',
                    'bool RateControl::splitbUsed(const char bused[], RateControlEntry *rce)',
                    'if (idx >= rce->rpsData.numberOfPictures)',
                    'if (!parseRateControlIntToken(tmpStr, bUsed) || bUsed < 0 || bUsed > 1)',
                    'rce->rpsData.bUsed[idx] = bUsed > 0;',
                    'idx++;',
                    'if (idx != rce->rpsData.numberOfPictures)',
                    'double RateControl::forwardMasking(Frame* curFrame, double q)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': 'if (e < 10)\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ratecontrol stats-line parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
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
                    'inline int calcScale(uint64_t x)',
                    'if (!m_param->bMultiPassOptRPS)',
                    'int scenecut = 0;',
                    'e = parseStatsLineFields(p + consumedPrefix, picType, qpRc, qpAq, qNoVbv, qRceq,',
                    'rcePocOrder->scenecut = scenecut != 0;',
                    'char deltaPOC[128] = {};',
                    'char bUsed[40] = {};',
                    'rce->rpsData.numberOfPictures,',
                    'deltaPOC, sizeof(deltaPOC), bUsed, sizeof(bUsed))',
                    'rce->rpsIdx = -1;',
                    '&& splitdeltaPOC(deltaPOC, rce)',
                    '&& splitbUsed(bUsed, rce) ? 18 : -1;',
                    'if ((!m_param->bMultiPassOptRPS && e != 14) || (m_param->bMultiPassOptRPS && e != 18))',
                    'bool RateControl::splitdeltaPOC(const char deltapoc[], RateControlEntry *rce)',
                    'if (idx >= rce->rpsData.numberOfPictures)',
                    'if (!parseRateControlIntToken(tmpStr, deltaPOC))',
                    'rce->rpsData.deltaPOC[idx] = deltaPOC;',
                    'idx++;',
                    'if (idx != rce->rpsData.numberOfPictures)',
                    'bool RateControl::splitbUsed(const char bused[], RateControlEntry *rce)',
                    'if (idx >= rce->rpsData.numberOfPictures)',
                    'if (!parseRateControlIntToken(tmpStr, bUsed) || bUsed < 0 || bUsed > 1)',
                    'rce->rpsData.bUsed[idx] = bUsed > 0;',
                    'idx++;',
                    'if (idx != rce->rpsData.numberOfPictures)',
                    'double RateControl::forwardMasking(Frame* curFrame, double q)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'stats-file loading must finish parseStatsLineFields and RPS token splitting before accepting an 18-field RPS entry')

    print('Ratecontrol stats-line parse guard tests passed')


if __name__ == '__main__':
    main()
