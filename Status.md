# x265 Yuuki Asuna Mod - 项目状态

## 已完成

### 2026-04-04: CMake 4.x 升级与依赖更新

1. **CMakeLists.txt 更新**
   - `cmake_minimum_required` 从 3.16 升级到 4.0
   - 移除已废弃的 policy 设置 (CMP0025 OLD, CMP0054 OLD)
   - 升级 C++ 标准从 C++11 到 C++17
   - 新增 `ENABLE_UNITY_BUILD` 和 `LINK_WARNING_AS_ERROR` 选项
   - 添加目录级别 `include_directories()` 修复 OBJECT 库编译

2. **依赖版本更新**

| 依赖项 | 旧版本 | 新版本 |
|--------|--------|--------|
| CMake | 3.16 | **4.0** |
| FFmpeg | n4.4 | **n8.1** |
| mimalloc | v2.2.4-AC | **v3.1.5** |
| Clang/LLVM | 自动 | **22.1.2** |
| sphinx | 未指定 | **≥9.1.0** |
| sphinx-rtd-theme | 未指定 | **≥3.1.0** |

3. **API 兼容性验证**
   - FFmpeg 8.1: ✅ 兼容（已使用现代 send/receive API）
   - mimalloc v3: ✅ 兼容（mi_malloc_aligned/mi_free 不变）

### 之前完成

- [x] GitHub Actions 构建成功
- [x] 修复 mimalloc 链接问题
- [x] 修复 mimalloc 版本硬编码问题

## 待办事项

- [ ] 验证 GitHub Actions 构建成功
- [ ] 测试各平台编译

## 注意事项

- mimalloc v3.0.x 在 Windows Clang 下有 `_TEB` 类型编译错误，已改用 v3.1.5
- CMake 4.x 需要目录级别的 `include_directories()` 以确保 OBJECT 库继承 include 路径
