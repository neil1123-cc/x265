# x265 Yuuki Asuna Mod - 项目状态

## 已完成

- [x] GitHub Actions 构建成功
- [x] 修复 mimalloc 链接问题（使用完整路径）
- [x] 修复 mimalloc 版本硬编码问题（动态查找版本目录）
- [x] 更新 cmake_minimum_required 到 3.16
- [x] 优化 build.yml：
  - 添加 Node.js 24 支持
  - 优化 CMake 安装方式（通过 pacman 直接安装）
  - 添加 `fail-fast: false` 允许所有 matrix 任务完成
  - 优化缓存 key 包含 FFmpeg 版本号

## 待办事项

- [ ] 监控后续构建结果
- [ ] 考虑添加 ucrt toolchain 支持（目前被注释）

## 构建配置

| 参数 | 值 |
|------|---|
| 目标架构 | x86-64, haswell, skylake, alderlake, raptorlake, arrowlake, znver2, znver3, znver4, znver5 |
| 工具链 | clang |
| FFmpeg | n4.4 |
| mimalloc | v2.2.4-AC |
| PGO | 启用 |

## 最近修改

### 2026-04-03
- 优化 CMakeLists.txt 和 build.yml
