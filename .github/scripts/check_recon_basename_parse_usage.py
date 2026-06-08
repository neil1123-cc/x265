#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
FORBIDDEN_SNIPPETS = (
    'const char* token = std::strtok(temp, ".");',
    'std::snprintf(buf, std::strlen(temp) + 7, "%s-%d.yuv", token, view);',
    'char* temp = new char[reconNameLen + 1];',
    'char* buf = new char[std::strlen(temp) + 7];',
)
REQUIRED_SNIPPETS = (
    'std::vector<std::string> derivedReconNames;',
    'if (param->bEnableAlpha || param->numViews > 1)',
    'std::string temp = reconfn[0];',
    "size_t extensionPos = temp.find_last_of('.');",
    'if (extensionPos == 0)',
    'x265_log(param, X265_LOG_ERROR, "recon file name must include a non-empty base name for alpha or multiview output\\n");',
    'if (extensionPos != std::string::npos)',
    'temp.erase(extensionPos);',
    'if (temp.empty())',
    'derivedReconNames.reserve(param->numLayers);',
    'derivedReconNames.push_back(temp + "-" + std::to_string(view) + ".yuv");',
    'reconfn[view] = derivedReconNames.back().c_str();',
)
REGION_START = 'std::vector<std::string> derivedReconNames;'
REGION_END = 'for (int i = 0; i < param->numLayers; i++)'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
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
    region = get_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden recon basename parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing recon basename parse guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'std::vector<std::string> derivedReconNames;',
                'if (param->bEnableAlpha || param->numViews > 1)',
                'std::string temp = reconfn[0];',
                "size_t extensionPos = temp.find_last_of('.');",
                'if (extensionPos == 0)',
                'x265_log(param, X265_LOG_ERROR, "recon file name must include a non-empty base name for alpha or multiview output\\n");',
                'if (extensionPos != std::string::npos)',
                'temp.erase(extensionPos);',
                'if (temp.empty())',
                'derivedReconNames.reserve(param->numLayers);',
                'derivedReconNames.push_back(temp + "-" + std::to_string(view) + ".yuv");',
                'reconfn[view] = derivedReconNames.back().c_str();',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Recon basename derivation must validate the base filename before erasing the extension and publishing per-layer recon names'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed recon basename parsing guardrails in x265cli.cpp')
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

    print('Recon basename parse usage validated')


if __name__ == '__main__':
    main()
