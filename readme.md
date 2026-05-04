# x265 Enhanced Builds for Windows/MSYS2

[![Build](https://github.com/neil1123-cc/x265/actions/workflows/build.yml/badge.svg)](https://github.com/neil1123-cc/x265/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/neil1123-cc/x265?include_prereleases)](https://github.com/neil1123-cc/x265/releases)
[![License](https://img.shields.io/github/license/neil1123-cc/x265)](COPYING)

这是一个跟随 x265 官方版本演进的增强构建仓库。它面向 Windows/MSYS2 维护预编译发布、现代化 C++17 构建链、常用媒体输入/输出扩展，以及来自 Yuuki / Kyouko 系 mod 的编码功能增强。

本仓库不是 x265 上游官方发行版；如果只需要官方源码、官方文档或商业授权信息，请优先查看 x265 上游项目。

## 增强点概览

| 方向 | 内容 |
| --- | --- |
| 构建现代化 | 源码构建使用 C++17，最低要求 CMake 4.0，并维护 Ninja / MSYS2 CLANG64 / clang / lld 发布链路。 |
| Windows 发布 | GitHub Actions 自动产出 Windows 64-bit 预编译包，覆盖多个 Intel / AMD CPU 目标。 |
| 多 bit-depth | 正式包提供 8-bit、10-bit、12-bit 和 all-in-one CLI。 |
| 输入扩展 | 支持 FFmpeg/LAVF、AviSynth、VapourSynth 输入路径。 |
| 容器输出 | 支持 RAW HEVC、MKV、MP4、GOP 输出；MP4 由 L-SMASH 支撑。 |
| 编码增强 | 保留并维护 Yuuki / Kyouko 系增强内容，覆盖 AQ、GOP/lookahead、场景切换、码控、SEI、日志和进度显示等方向。 |
| CI 验证 | 覆盖 L-SMASH patch/build/smoke、RAW/MKV/MP4/LAVF smoke、open-GOP、CRA、strict-CBR、时间基和封装边界用例。 |
| Profiling / PGO | 提供 profiling 构建和 PGO profdata 维护链路，用于性能验证和发布维护。 |

## 适合谁

- 想直接下载 Windows 64-bit x265 CLI 的用户。
- 需要 `.mkv`、`.mp4` 或 `.gop` 输出，而不只是 `.hevc` 裸流的用户。
- 需要读取常见媒体文件，或接入 AviSynth / VapourSynth 工作流的用户。
- 需要 Yuuki / Kyouko 系增强参数，而不是纯上游 CLI 的用户。
- 需要可复现 CI 构建、profiling 或 PGO 维护链路的开发者。

## 下载和选择构建

前往 [Releases](https://github.com/neil1123-cc/x265/releases) 下载发布资产。实际文件名以每个 release 页面为准，通常会按 CPU 架构和用途拆分。

### 普通编码用户

优先下载正式编码器包。正式包通常包含：

- 8-bit CLI
- 10-bit CLI
- 12-bit CLI
- all-in-one CLI

如果不确定该用哪个，先选 `x86-64` 的 all-in-one 可执行文件。

### Profiling / PGO 用户

profiling 和 `llvm-profdata` 相关资产主要用于 profile 采集、PGO 维护和工具链验证；普通编码用户通常不需要下载。

### CPU 架构怎么选

| CPU 架构 | 适用范围 | 建议 |
| --- | --- | --- |
| `x86-64` | 通用 x86-64 | 不确定型号时选它 |
| `haswell` | Intel Haswell 及更新 | Intel 4 代及更新平台 |
| `skylake` | Intel Skylake 及更新 | Intel 6 代及更新平台 |
| `alderlake` | Intel Alder Lake | Intel 12 代平台 |
| `raptorlake` | Intel Raptor Lake | Intel 13/14 代平台 |
| `arrowlake` | Intel Arrow Lake / Core Ultra 200 | 新一代 Intel 客户端平台 |
| `znver2` | AMD Zen 2 | Ryzen 3000 / EPYC Rome |
| `znver3` | AMD Zen 3 | Ryzen 5000 / EPYC Milan |
| `znver4` | AMD Zen 4 | Ryzen 7000 / EPYC Genoa |
| `znver5` | AMD Zen 5 | Ryzen 9000 / EPYC Turin |

专用架构构建可能使用目标 CPU 才支持的指令；不确定时请选择 `x86-64`。

## 功能说明

### 输入

- FFmpeg/LAVF：读取常见媒体容器和格式。
- AviSynth：接入 AVS 脚本工作流。
- VapourSynth：接入 VPY 脚本工作流。

### 输出

```bash
# RAW HEVC
x265-win64-<cpu>-all.exe input.y4m -o output.hevc

# MKV
x265-win64-<cpu>-all.exe input.y4m -o output.mkv

# MP4
x265-win64-<cpu>-all.exe input.y4m -o output.mp4
```

#### GOP 输出

`.gop` 不是最终播放容器，而是一组面向后续 MP4 mux 的分段输出。编码到 `.gop` 时，x265 会在目标目录生成：

- `output.gop`：分段清单，记录 options、headers 和 GOP data 文件名。
- `output.options`：mux 所需的视频参数，例如分辨率、帧率、timebase、SAR、色彩信息等。
- `output.headers`：VPS / SPS / PPS 等 HEVC headers。
- `output-000000.hevc-gop-data`、`output-000001.hevc-gop-data` 等：按 IDR/GOP 切分的 HEVC 数据分片，包含 PTS / DTS 信息。

```bash
x265-win64-<cpu>-all.exe input.y4m -o output.gop
```

要得到可播放的 MP4，需要使用 [msg7086/gop_muxer](https://github.com/msg7086/gop_muxer) 进行 mux：

```bash
gop_muxer output.gop
```

`gop_muxer` 会读取 `.gop` 清单引用的同目录 sidecar 文件，并输出同 basename 的 `.mp4`。例如 `output.gop` 会生成 `output.mp4`。

注意事项：

- 不要只移动 `.gop` 文件；`.options`、`.headers` 和 `*.hevc-gop-data` 必须和它保持相对路径一致。
- `gop_muxer` 接受一个或多个 `.gop` 清单，用于把分段结果 mux 成 MP4；日常单文件输出通常只需要传一个 `.gop`。
- 目标 `.mp4` 如果已存在，`gop_muxer` 会直接覆盖，不会二次确认。
- GOP 输出路径来自 Yuuki/Kyouko 系增强能力；普通 MP4 输出可直接使用 `-o output.mp4`，不需要额外 mux 工具。

### CLI 增强方向

增强内容来自 Yuuki / Kyouko 系 mod，并在本仓库中继续整理和验证。重点方向包括：

- AQ / 视觉优化：`--aq-motion`、`--selective-sao` 等。
- GOP / lookahead：`--gop-lookahead`、`--lookahead-slices`、`--hist-scenecut`、`--scenecut-bias`、`--fades`、`--radl` 等。
- 码控和直播场景：`--strict-cbr`、`--vbv-live-multi-pass`、`--abr-ladder` 等。
- bitstream / SEI：`--single-sei`、`--max-ausize-factor`、`--log2-max-poc-lsb` 等。
- 并行与分析：`--threaded-me`、`--temporal-layers` 等。
- 日志和交互：`--log-file`、`--log-file-level`、`--stylish` 等。
- 兼容性开关：`--allow-non-conformance` 等。

具体参数、默认值和帮助文本以当前二进制输出为准：

```bash
x265-win64-<cpu>-all.exe --fullhelp
```

## 构建要求

当前发布链路面向 Windows + MSYS2 `CLANG64`，使用 C++20、CMake 4.0+、Ninja、NASM、clang/lld、ThinLTO、FFmpeg、L-SMASH 和 mimalloc。

| 项目 | 要求 / 说明 |
| --- | --- |
| C++ 标准 | C++20 |
| CMake | 4.0+ |
| NASM | 2.13.0+（启用 x86 ASM 时） |
| Windows 发布环境 | MSYS2 `CLANG64` |
| 编译器/链接器 | release CI 使用 clang、lld、libc++ |

## 发布链路依赖

这些依赖由 CI 安装、构建或缓存；本地构建时请以实际启用的 CMake 选项和系统环境为准。

| 依赖 | CI 来源 | 用途 |
| --- | --- | --- |
| FFmpeg | `FFmpeg/FFmpeg@n8.1` | LAVF 输入、smoke 素材生成和 ffprobe 校验；版本由 update-deps workflow 跟踪。 |
| L-SMASH | `vimeo/l-smash` master SHA + 本仓库 patch | MP4 输出；CI 由 update-deps workflow 跟踪上游 master 并把解析出的 commit 写入 shared deps，再应用 `.github/patches/l-smash-clang-coff-refptr.patch` 后构建和 smoke test。 |
| mimalloc | `microsoft/mimalloc@v3.3.1` | release 构建默认启用；版本由 update-deps workflow 跟踪。 |
| obuparse | `dwbuiten/obuparse@v2.0.2` | L-SMASH AV1 OBU helper 依赖；CI 使用 `obuparse-v2.0.2-clang-v1` cache key 缓存安装产物，版本由 update-deps workflow 跟踪。 |

## 本地构建示例

```bash
git clone https://github.com/neil1123-cc/x265.git
cd x265

cmake -GNinja x265/source -B build/all \
  -DCMAKE_PREFIX_PATH=/usr/local \
  -DTARGET_CPU=x86-64 \
  -DENABLE_SHARED=OFF \
  -DENABLE_LAVF=ON \
  -DENABLE_STATIC_LAVF=ON \
  -DENABLE_MKV=ON \
  -DENABLE_LSMASH=ON \
  -DUSE_MIMALLOC=ON \
  -DENABLE_UNITY_BUILD=ON \
  -DCMAKE_ASM_NASM_FLAGS=-w-macro-params-legacy

ninja -C build/all
```

常用 CMake 选项：

| 选项 | 说明 |
| --- | --- |
| `TARGET_CPU` | 目标 CPU 架构 |
| `ENABLE_LAVF` | 启用 FFmpeg/LAVF 输入 |
| `ENABLE_STATIC_LAVF` | 静态链接 LAVF 相关组件 |
| `ENABLE_MKV` | 启用 MKV 输出 |
| `ENABLE_LSMASH` | 启用 L-SMASH / MP4 输出 |
| `USE_MIMALLOC` | 启用 mimalloc |
| `ENABLE_UNITY_BUILD` | 启用 unity build |

更完整、更新的构建细节请直接查看 CI：

- `.github/actions/setup-windows-deps/action.yml`
- `.github/workflows/build.yml`
- `.github/workflows/build-profiling.yml`
- `.github/workflows/build-pgo.yml`
- `.github/workflows/update-deps.yml`

## CI 覆盖

主构建 workflow 会覆盖：

- L-SMASH patch / build / smoke test
- 多 bit-depth CLI 编译
- RAW / MKV / MP4 / LAVF 输入 smoke tests
- open-GOP、CRA、strict-CBR、时间基和封装边界用例
- profiling / PGO 相关构建链路

## 来源和致谢

- [x265](https://bitbucket.org/multicoreware/x265_git) - MulticoreWare 官方编码器
- [x265-Yuuki-Asuna](https://github.com/msg7086/x265-Yuuki-Asuna) - Yuuki mod 作者，本仓库增强内容来源之一
- [AmusementClub/x265](https://github.com/AmusementClub/x265) - Kyouko mod 来源，本仓库增强内容来源之一
- [FFmpeg](https://ffmpeg.org/) - 多媒体输入和工具链生态
- [vimeo/l-smash](https://github.com/vimeo/l-smash) - 当前 CI 使用的 L-SMASH 来源，配合本仓库 patch 提供 MP4 封装支持
- [gop_muxer](https://github.com/msg7086/gop_muxer) - GOP 分段输出的 MP4 mux 工具
- [mimalloc](https://github.com/microsoft/mimalloc) - Microsoft allocator

## 许可证

x265 使用 GNU GPL v2 许可证；详见 [COPYING](COPYING)。商业授权请参考 x265 上游项目说明。

如遇本 fork patch、构建脚本或发布包相关问题，请在本仓库提交 issue；上游 x265 问题请反馈给上游项目。