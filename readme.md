# x265 HEVC 编码器

## Yuuki Asuna Mod

![](yande.re-211430.png)

|  Branch             |[Yuuki](https://github.com/msg7086/x265-Yuuki-Asuna/tree/Yuuki)|[Asuna](https://github.com/msg7086/x265-Yuuki-Asuna/tree/Asuna)|
|---------------------|-------------------|-------------------|
|  Base branch        | Stable (3.5)      | Old Stable (3.4)  |
|                     | ![](Yuuki.jpg)    | ![](Asuna.jpg)    |

静态链接的 x265 Yuuki mod 编码器，集成多种功能支持。

## 特性

- **静态链接** - 无外部依赖，开箱即用
- **多 CPU 优化** - 支持 x86-64、Haswell、Skylake、Alderlake、Raptorlake、Arrow Lake、Zen 2/3/4/5 等多款 CPU
- **高比特深度** - 支持 8-bit、10-bit、12-bit 和全深度模式
- **PGO 优化** - Profile-Guided Optimization 提升性能
- **LTO 优化** - Link-Time Optimization 减少体积、提升速度
- **mimalloc** - 微软高性能内存分配器

## 依赖库

| 组件 | 版本 | 说明 |
|------|------|------|
| FFmpeg | n8.1 | 输入支持 |
| mimalloc | v3.2.8 | 高性能内存分配器 |
| L-SMASH | latest | MP4/MOV 输出支持 |
| obuparse | latest | AV1 解析支持 |

## 编译环境

- **操作系统**: Windows
- **工具链**: MSYS2 CLANG64
- **编译器**: Clang/LLVM
- **汇编器**: NASM

## 下载

前往 [Releases](https://github.com/neil1123-cc/x265/releases) 页面下载最新版本。

## 使用方法

```bash
# 基本编码
x265 input.y4m -o output.hevc

# 使用预设
x265 --preset slower --tune grain input.y4m -o output.hevc

# 指定码率
x265 --bitrate 5000 input.y4m -o output.hevc
```

## 许可证

x265 采用 [GNU GPL](https://www.gnu.org/licenses/gpl-2.0.html) 许可证，也可获取商业许可。

## 致谢

- [x265](https://bitbucket.org/multicoreware/x265_git) - MulticoreWare
- [x265-Yuuki-Asuna](https://github.com/msg7086/x265-Yuuki-Asuna) - Yuuki mod
- [FFmpeg](https://ffmpeg.org/) - FFmpeg 项目
- [mimalloc](https://github.com/microsoft/mimalloc) - Microsoft
- [L-SMASH](https://github.com/vimeo/l-smash) - Vimeo

---

To report a bug due to patches, create a new issue here. To report a x265 bug, please visit their repository or mailing list.
