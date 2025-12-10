# llm_demo_system_info

## 概述

`llm_demo_system_info.cpp` 是一个系统信息检测工具，用于显示当前环境的硬件和软件信息，特别是针对 ARM 架构的 MNN LLM 特性检测。

## 功能特性

### 🔍 系统信息检测
- **操作系统信息**：显示系统名称、版本和架构类型
- **CPU架构识别**：自动识别 x86_64、ARM64、ARM32 等架构
- **硬件特性检测**：检查运行时和编译时的 NEON 指令集支持

### ⚡ ARM 优化特性检测
- **NEON 指令集**：检测编译时和运行时的 NEON 支持
- **扩展指令集**：检测 ASIMD、FP16、FPHP 等指令集
- **向量化支持**：检测 SVE 和 SVE2 可扩展向量扩展
- **硬件能力**：通过 `/proc/cpuinfo` 和系统调用获取硬件能力

### 🔧 平台兼容性
- **Linux 系统**：完整支持，通过 `uname()` 和 `/proc` 接口
- **ARM 架构**：主要支持目标，包含详细的 ARM 特性检测
- **x86 架构**：基本支持，显示通用信息

## 编译和使用

### 编译依赖
```bash
# 确保启用 ARM 相关编译选项
-DMNN_ARM82=1
-DMNN_USE_NEON=1
```

### 编译命令
```bash
make llm_demo_system_info
```

### 运行输出示例
```
========================================
    MNN LLM System Information
========================================
OS: Linux 5.15.0-91-generic (aarch64)
Architecture: ARM64 (AArch64)
NEON Support:
  Compile-time: YES
  Runtime: YES
Hardware Capabilities:
  ASIMD: YES
  FP16: YES
  FPHP: YES
  SVE: NO
  SVE2: NO
CPU Info:
  Processor: ARM Cortex-A72
  Cores: 4
  Clock: 1.5GHz
```

## 技术特性

### 检测机制
1. **编译时检测**：通过预处理器宏定义
2. **运行时检测**：通过系统调用和硬件寄存器
3. **混合检测**：结合编译器和运行时信息

### 支持的指令集
- **NEON**：ARM SIMD 指令集（ARMv7+）
- **ASIMD**：ARM 高级 SIMD 用于加密
- **FP16**：半精度浮点运算
- **FPHP**：半精度性能提升
- **SVE/SVE2**：可扩展向量扩展（ARMv8+）

### 平台特定实现
```cpp
#ifdef __aarch64__
    // ARM64 特定检测
    unsigned long hwcaps = getauxval(AT_HWCAP);
    bool has_asimd = hwcaps & HWCAP_ASIMD;
    bool has_fp16 = hwcaps & HWCAP_FP16;
#endif
```

## 应用场景

### 🎯 性能优化
- **指令集选择**：根据硬件特性选择最优的代码路径
- **编译优化**：为特定硬件生成优化的指令
- **基准测试**：确保测试环境具备必要硬件能力

### 🔧 开发调试
- **环境验证**：验证部署环境是否满足要求
- **问题诊断**：识别性能问题和硬件限制
- **兼容性检查**：验证不同平台的兼容性

## 技术细节

### 宏定义层次
```cpp
// 系统级检测
#ifdef __linux__
// Linux 特定功能
#endif

// 架构级检测
#ifdef __aarch64__
// ARM64 特定功能
#elif __x86_64__
// x86_64 特定功能
#endif

// 指令集级检测
#ifdef MNN_USE_NEON
// NEON 优化代码路径
#endif
```

### 能力检测流程
1. **定义兼容宏**：处理不同内核版本的差异
2. **获取硬件能力**：通过 `getauxval()` 系统调用
3. **解析特性**：检查特定的 HWCAP 标志位
4. **报告结果**：格式化输出检测结果

## 维护说明

### 代码风格
- 使用标准 C++11 特性
- 兼容 MNN 项目的代码风格
- 添加详细的注释说明

### 测试验证
```bash
# 编译测试
make llm_demo_system_info

# 功能测试
./llm_demo_system_info

# 跨平台测试（在支持的平台上）
./llm_demo_system_info
```

### 扩展指南
添加新特性检测：

1. **添加宏定义**：在文件头部定义新特性宏
2. **实现检测逻辑**：添加运行时检测代码
3. **更新输出**：在结果中显示新特性状态
4. **添加文档**：更新本 README 说明

## 故障排除

### 常见问题
- **编译错误**：检查 ARM 架构的编译选项
- **运行时错误**：确保目标平台支持相应的系统调用
- **检测不准确**：验证内核版本和工具链版本

### 调试技巧
```cpp
#ifdef DEBUG_SYSTEM_INFO
    printf("Debug: HWCAP value = 0x%lx\n", hwcaps);
#endif
```

---

**注意**：
- 该工具主要用于 MNN LLM 项目的开发和调试
- 对于生产环境，建议根据检测能力动态选择优化路径
- 具体的硬件支持请参考目标平台的官方文档

**版本**：
- 初始版本：基于 MNN llm_demo 项目
- 当前版本：支持 ARM64/x86_64 平台
- 维护者：MNN LLM 团队