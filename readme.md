# x265 Kyouko 4.1-AC

[![Build](https://github.com/neil1123-cc/x265/actions/workflows/build.yml/badge.svg)](https://github.com/neil1123-cc/x265/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/neil1123-cc/x265?include_prereleases)](https://github.com/neil1123-cc/x265/releases)
[![License](https://img.shields.io/github/license/neil1123-cc/x265)](LICENSE)

基于官方 x265 4.1 + 242 commits 的增强版 HEVC 编码器。

## 特性

- **多架构优化构建** - 支持 x86-64、Haswell、Skylake、Alder Lake、Raptor Lake、Arrow Lake、Zen 2/3/4/5
- **多 bit-depth 支持** - 8-bit、10-bit、12-bit 和全深度模式
- **LAVF 输入支持** - 支持 FFmpeg 输入格式（mov, mkv, ts, avi 等）
- **L-SMASH/MKV 输出** - 支持 MP4 和 MKV 容器输出
- **mimalloc 内存分配器** - 微软高性能内存分配器
- **PGO + LTO 优化** - Profile-Guided Optimization 和 Link-Time Optimization

## 依赖版本

| 组件 | 版本 | 说明 |
|------|------|------|
| x265 | 4.1 + Kyouko mod | HEVC 编码器 |
| FFmpeg | n8.1 | LAVF 输入支持 |
| mimalloc | v3.2.8 | 高性能内存分配器 |
| L-SMASH | `04e39f1` | MP4/MOV 输出支持 |
| obuparse | `c2156b4` | AV1 解析支持 |
| Clang | 22.1.3 | 编译器 (MSYS2 CLANG64) |
| CMake | 4.3.1 | 构建系统 |
| NASM | 3.01 | 汇编器 |

## 下载

前往 [Releases](https://github.com/neil1123-cc/x265/releases) 页面下载对应 CPU 架构的版本。

| 文件 | CPU 架构 | 推荐 |
|------|----------|------|
| x86-64 | 通用 x86-64 | 兼容性最好 |
| haswell | Intel Haswell 及更新 | Intel 4代+ |
| skylake | Intel Skylake 及更新 | Intel 6代+ |
| alderlake | Intel Alder Lake | Intel 12代 |
| raptorlake | Intel Raptor Lake | Intel 13代 |
| arrowlake | Intel Arrow Lake | Intel 14代/酷睿Ultra |
| znver2 | AMD Zen 2 | Ryzen 3000 |
| znver3 | AMD Zen 3 | Ryzen 5000 |
| znver4 | AMD Zen 4 | Ryzen 7000 |
| znver5 | AMD Zen 5 | Ryzen 9000 |

每个压缩包包含：
- `x265-8bit.exe` - 8-bit 编码器
- `x265-10bit.exe` - 10-bit 编码器
- `x265-12bit.exe` - 12-bit 编码器
- `x265.exe` - 全深度编码器（自动选择）

## 使用方法

### 基本编码

```bash
# 基本使用
x265 input.mp4 -o output.hevc

# 使用预设
x265 --preset slower --tune grain input.mp4 -o output.hevc

# 指定码率
x265 --bitrate 5000 input.mp4 -o output.hevc

# 指定 CRF 质量
x265 --crf 22 input.mp4 -o output.hevc
```

### 高级选项

```bash
# 10-bit 编码（HDR 推荐）
x265-10bit.exe --crf 20 --preset slow \
  --master-display "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)" \
  --max-cll "1000,400" \
  input.mp4 -o output.hevc

# 多线程编码
x265 --threads 16 --pools "+" input.mp4 -o output.hevc

# 输出到 MKV
x265 input.mp4 -o output.mkv

# 输出到 MP4
x265 input.mp4 -o output.mp4
```

### 常用预设

| 预设 | 编码速度 | 压缩效率 | 适用场景 |
|------|----------|----------|----------|
| ultrafast | 最快 | 最低 | 实时编码 |
| superfast | 很快 | 低 | 快速预览 |
| veryfast | 快 | 中低 | 快速编码 |
| faster | 较快 | 中 | 一般用途 |
| fast | 中快 | 中高 | 日常使用 |
| medium | 中等 | 高 | 推荐默认 |
| slow | 较慢 | 很高 | 高质量归档 |
| slower | 慢 | 更高 | 极高质量 |
| veryslow | 很慢 | 最高 | 最终版本 |
| placebo | 最慢 | 最高 | 极限质量 |

## 编译

### 环境要求

- Windows 10/11
- [MSYS2 CLANG64](https://www.msys2.org/)
- Git
- CMake 4.0+
- Ninja
- NASM 3.0+

### 编译步骤

```bash
# 安装依赖
pacman -S mingw-w64-clang-x86_64-clang mingw-w64-clang-x86_64-cmake \
          mingw-w64-clang-x86_64-ninja mingw-w64-clang-x86_64-nasm

# 克隆仓库
git clone https://github.com/neil1123-cc/x265.git
cd x265/source

# 构建
cmake -GNinja -B build -DENABLE_SHARED=OFF -DENABLE_LAVF=ON
ninja -C build
```

### CMake 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_SHARED` | ON | 构建动态库 |
| `ENABLE_LAVF` | OFF | FFmpeg 输入支持 |
| `ENABLE_LSMASH` | OFF | L-SMASH 输出支持 |
| `ENABLE_MKV` | OFF | MKV 输出支持 |
| `USE_MIMALLOC` | OFF | 使用 mimalloc |
| `ENABLE_UNITY_BUILD` | OFF | Unity Build 加速编译 |
| `TARGET_CPU` | - | 目标 CPU 架构 |

## 许可证

x265 采用 [GNU GPL v2](LICENSE) 许可证，也可获取商业许可。

## 致谢

- [x265](https://bitbucket.org/multicoreware/x265_git) - MulticoreWare
- [x265-Yuuki-Asuna](https://github.com/msg7086/x265-Yuuki-Asuna) - Yuuki mod 作者
- [FFmpeg](https://ffmpeg.org/) - FFmpeg 项目
- [mimalloc](https://github.com/microsoft/mimalloc) - Microsoft
- [L-SMASH](https://github.com/vimeo/l-smash) - Vimeo

---

To report a bug due to patches, create a new issue here. To report a x265 bug, please visit their repository or mailing list.
