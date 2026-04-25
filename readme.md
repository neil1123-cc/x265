# x265 4.1 Windows/MSYS2 Builds

[![Build](https://github.com/neil1123-cc/x265/actions/workflows/build.yml/badge.svg)](https://github.com/neil1123-cc/x265/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/neil1123-cc/x265?include_prereleases)](https://github.com/neil1123-cc/x265/releases)
[![License](https://img.shields.io/github/license/neil1123-cc/x265)](LICENSE)

这是一个面向 Windows/MSYS2 的 x265 4.1 增强构建分支，提供多 CPU 架构优化的预编译版本，并支持 MKV / MP4 输出。

## 特性

- **多架构优化构建** - 提供 `x86-64`、`haswell`、`skylake`、`alderlake`、`raptorlake`、`arrowlake`、`znver2`、`znver3`、`znver4`、`znver5`
- **多 bit-depth 发布** - 每个正式包都包含 8-bit、10-bit、12-bit 和 all-in-one 四种可执行文件
- **常见容器支持** - 支持 RAW HEVC、MKV 和 MP4 输出
- **LAVF 输入支持** - 可直接读取常见 FFmpeg 输入格式（mov、mkv、ts、avi 等）
- **面向下载用户的发布方式** - 正式编码器和 profiling 工具链都在 Releases 页面统一提供

## 下载

前往 [Releases](https://github.com/neil1123-cc/x265/releases) 页面下载对应版本。

### 正式发布资产

正式发布包文件名：

- `x265-win64-<cpu>-clang.<tag>.7z`

每个压缩包包含：

- `x265-win64-<cpu>-8bit.exe`
- `x265-win64-<cpu>-10bit.exe`
- `x265-win64-<cpu>-12bit.exe`
- `x265-win64-<cpu>-all.exe`

如果你只是普通使用，优先下载这一类。

### Profiling 发布资产

同一个 tag 下还会额外发布 profiling 资产：

- `x265-profiling-win64-<cpu>-clang.<tag>.7z`
- `llvm-profdata-win64-clang.<tag>.7z`（仅 `x86-64`）

`x265-profiling` 压缩包包含：

- `x265-profiling-win64-<cpu>-8b-lib.exe`
- `x265-profiling-win64-<cpu>-12b-lib.exe`
- `x265-profiling-win64-<cpu>-all.exe`

这一类主要给 profiling / PGO / 工具链验证使用，普通编码用户一般不需要下载。

### CPU 架构选择建议

| CPU 架构 | 适用范围 | 推荐 |
|---------|----------|------|
| `x86-64` | 通用 x86-64 | 不确定型号时优先选这个 |
| `haswell` | Intel Haswell 及更新 | Intel 4 代+ |
| `skylake` | Intel Skylake 及更新 | Intel 6 代+ |
| `alderlake` | Intel Alder Lake | Intel 12 代 |
| `raptorlake` | Intel Raptor Lake | Intel 13/14 代 |
| `arrowlake` | Intel Arrow Lake / Core Ultra 200 | 新一代 Intel 客户端平台 |
| `znver2` | AMD Zen 2 | Ryzen 3000 / Rome |
| `znver3` | AMD Zen 3 | Ryzen 5000 / Milan |
| `znver4` | AMD Zen 4 | Ryzen 7000 / Genoa |
| `znver5` | AMD Zen 5 | Ryzen 9000 / Turin |

如果你的 CPU 与目标优化架构不匹配，专用构建可能无法运行；不确定时请优先使用 `x86-64`。

## 使用方法

这个分支提供的是预编译 x265 可执行文件；具体命令行参数、预设、码率控制、HDR 选项等用法，建议直接查看 x265 官方文档：

- [x265 CLI 文档](https://x265.readthedocs.io/en/master/cli.html)
- [x265 官方文档首页](https://x265.readthedocs.io/)

如果你主要关心本仓库相对官方版额外提供的能力，可结合官方 CLI 文档重点留意下面这些扩展场景：

- 输出 `.hevc`：RAW HEVC
- 输出 `.mkv`：MKV 容器
- 输出 `.mp4`：MP4 容器
- 输出 `.gop`：GOP 封装输出
- 直接读取常见 FFmpeg/LAVF 输入格式

### 相对官方版额外可关注的功能/参数

除了上游 x265 常见参数外，这个分支还额外提供了或强化了下面这些能力：

- **容器与输入扩展**
  - MKV 输出
  - MP4 输出
  - GOP 输出（写入 `.gop`）
  - FFmpeg/LAVF 输入
- **GOP / slicetype 相关扩展参数**
  - `--gop-lookahead`
  - `--hist-scenecut`
  - `--scenecut-bias`
  - `--fades`
  - `--radl`
  - `--lookahead-slices`
- **其他这个分支里可见的扩展参数**
  - `--stylish`
  - `--selective-sao`
  - `--temporal-layers`
  - `--strict-cbr`
  - `--vbv-live-multi-pass`
  - `--single-sei`
  - `--max-ausize-factor`
  - `--log2-max-poc-lsb`
  - `--abr-ladder`

这些参数是否存在、默认值如何、以及帮助文本说明，可以直接运行对应可执行文件查看：

```bash
x265-win64-<cpu>-all.exe --fullhelp
```

日常参数选择仍可优先参考官方文档中的 `--preset`、`--crf`、`--bitrate`、bit-depth 与 HDR 相关说明；而上面这些“官方版没有或本分支特别值得留意”的能力，则以本仓库实际编译出的 `--fullhelp` 为准。

## 发布说明

Releases 页面当前会同时提供两类资产：

- **正式编码器包** - 面向日常下载和直接使用
- **profiling 工具链包** - 面向测试、分析和 PGO 维护

如果你只是下载来编码，通常只需要正式编码器包，不需要 profiling 包。

## 依赖与构建环境

仓库依赖版本会随 CI 更新流程演进，最新状态建议直接查看：

- `.github/actions/setup-windows-deps/action.yml`
- `.github/deps-cache.json`
- `.github/workflows/update-deps.yml`

当前构建环境核心特征：

- Windows + MSYS2 `CLANG64`
- CMake + Ninja
- NASM
- FFmpeg / L-SMASH / mimalloc
- ThinLTO 启用

## 编译

### 环境要求

- Windows 10/11
- [MSYS2 CLANG64](https://www.msys2.org/)
- Git
- CMake
- Ninja
- NASM

### 基本构建示例

```bash
# 克隆仓库
git clone https://github.com/neil1123-cc/x265.git
cd x265

# 示例：构建 x86-64 all-in-one CLI
cmake -GNinja x265/source -B build/all \
  -DCMAKE_PREFIX_PATH=/usr/local \
  -DTARGET_CPU=x86-64 \
  -DENABLE_SHARED=OFF \
  -DENABLE_LAVF=ON \
  -DENABLE_STATIC_LAVF=ON \
  -DENABLE_MKV=ON \
  -DENABLE_LSMASH=ON \
  -DUSE_MIMALLOC=ON \
  -DENABLE_UNITY_BUILD=ON
ninja -C build/all
```

### 常用 CMake 选项

| 选项 | 说明 |
|------|------|
| `TARGET_CPU` | 目标 CPU 架构 |
| `ENABLE_LAVF` | 启用 FFmpeg/LAVF 输入 |
| `ENABLE_MKV` | 启用 MKV 输出 |
| `ENABLE_LSMASH` | 启用 L-SMASH / MP4 输出 |
| `USE_MIMALLOC` | 启用 mimalloc |
| `ENABLE_UNITY_BUILD` | 启用 unity build |
| `ENABLE_STATIC_LAVF` | 静态链接 LAVF 相关组件 |

## 许可证

x265 采用 [GNU GPL v2](LICENSE) 许可证，也可获取商业许可。

## 致谢

- [x265](https://bitbucket.org/multicoreware/x265_git) - MulticoreWare 官方编码器
- [x265-Yuuki-Asuna](https://github.com/msg7086/x265-Yuuki-Asuna) - Yuuki mod 作者
- [AmusementClub/x265](https://github.com/AmusementClub/x265) - Kyouko mod 来源
- [FFmpeg](https://ffmpeg.org/) - FFmpeg 项目
- [mimalloc](https://github.com/microsoft/mimalloc) - Microsoft

---

To report a bug due to patches, create a new issue here. To report a x265 bug, please visit their repository or mailing list.
