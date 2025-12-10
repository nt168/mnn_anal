# vllm_bench - 支持图片提示词的LLM性能基准测试工具

## 概述

`vllm_bench` 是基于 `llm_bench_prompt.cpp` 扩展的LLM性能基准测试工具，专门增加了对图片提示词的支持。它可以帮助开发者测试多模态LLM模型的性能，包括图片理解和提示词处理能力。

## 新增功能

### 1. 图片提示词支持
- 支持本地图片文件作为提示词输入
- 自动构建包含 `<img>image_0</img>` 标记的多模态提示词
- 与vllm示例保持一致的图片处理逻辑

### 2. 新增命令行参数
```bash
-ipf, --image-file <filename>  指定图片文件路径
```

### 3. 增强的提示词类型判断
工具现在支持四种提示词类型，优先级从高到低：
- `image`: 图片提示词模式（使用 `-ipf` 参数）
- `file`: 文本文件模式（使用 `-pf` 参数）
- `variable`: 可变token模式（使用 `-vp` 参数）
- `fix`: 固定token模式（默认模式）

## 使用方法

### 基本语法
```bash
./vllm_bench [options]
```

### 图片提示词测试示例
```bash
# 使用图片进行性能测试
./vllm_bench -m ~/models/Qwen3-0.6B-MNN/config.json --kv-cache true -ipf /path/to/image.jpg -v 1 -n-prompt 10 -n-gen 5

# 结合详细输出查看执行过程
./vllm_bench --image-file cat.jpg --verbose 1 --model config.json
```

### 传统文本测试
原有功能完全保持不变：
```bash
# 文件模式
./vllm_bench -pf prompt.txt -v 1

# 固定token模式
./vllm_bench -p 512 -n 128

# 可变token模式
./vllm_bench -vp 1 -p 256
```

## 重要限制

1. **图片模式仅支持 `--kv-cache true`**
   - llama.cpp模式（`--kv-cache false`）主要是token级性能测试，不支持图片输入
   - 系统会显示警告并自动跳过图片参数

2. **图片处理当前为占位实现**
   - 当前版本使用420x420的占位图像数据
   - 生产环境需要集成真实的图片解码库（如stb_image）

3. **模型兼容性**
   - 需要使用支持多模态输入的模型配置
   - 确保模型具有视觉处理能力

## 核心架构改动

### 1. 数据结构扩展
```cpp
struct TestParameters {
    // 原有字段...
    std::string imageFilePath;      // 新增：图片文件路径
};

struct TestInstance {
    // 原有字段...
    std::string imageFilePath;      // 新增：图片文件路径
    std::string pType;              // 更新：支持 "image" 类型
};
```

### 2. 核心功能函数
```cpp
// 图片加载
static PromptImagePart loadImageFromFile(const std::string& filePath);

// 多模态提示词构建
static MultimodalPrompt buildMultimodalPrompt(const std::string& textPrompt, const std::string& imageFile);
```

### 3. 测试流程集成
- `llm_demo`分支：支持完整的multimodal调用
- `llama.cpp`分支：显示警告，保持原有token测试

## 输出信息增强

### 详细模式输出
启用`--verbose 1`后，图片模式会显示：
- 图片文件路径和尺寸
- 多模态调用标识
- 性能指标（vision时间等）

### 性能统计
- `pType`列显示当前测试类型（`image`, `file`, `variable`, `fix`）
- 保持原有的所有性能指标输出格式

## 编译和部署

### 构建要求
更新了`transformers/llm/engine/CMakeLists.txt`：
```cmake
add_executable(vllm_bench ${CMAKE_CURRENT_LIST_DIR}/phy_tools/vllm_bench.cpp)
target_link_libraries(vllm_bench ${LLM_DEPS})
```

### 编译命令
```bash
cd build
make vllm_bench
```

## 示例场景

### 1. 纯图片性能测试
测试模型对图像的处理能力：
```bash
./vllm_bench --image-file test.jpg --verbose 1 --model config.json --kv-cache true
```

### 2. 对比测试
比较图片模式和文本模式的性能差异：
```bash
# 图片模式
./vllm_bench --image-file test.jpg --n-prompt 50 -n-gen 20 --fp result.txt

# 文件模式（相同文本内容）
./vllm_bench --prompt-file prompt.txt --n-prompt 50 -n-gen 20 --fp result.txt
```

### 3. 调试模式
查看详细的执行流程：
```bash
./vllm_bench --image-file test.jpg --verbose 1 --n-repeat 1 --kv-cache true
```

## 故障排除

### 常见问题

1. **编译错误**
   - 确保包含了正确的头文件路径
   - 检查MNN版本支持多模态功能

2. **运行时错误**
   - 验证图片文件存在且可读
   - 确认模型配置支持视觉输入

3. **性能异常**
   - 检查是否使用了正确的测试模式（kv-cache=true）
   - 验证模型文件完整性

### 调试建议
- 使用 `--verbose 1` 查看详细执行过程
- 检查输出中的 `pType` 字段确认测试模式
- 与原始 `llm_bench_prompt` 对比确保基准一致

## 未来改进

1. **真实图像解码**
   - 集成stb_image或MNN CV模块
   - 支持多种图像格式（JPEG, PNG, etc.）

2. **高级图像处理**
   - 图像预处理选项
   - 批量图像测试支持

3. **性能优化**
   - 专门的vision性能统计
   - GPU加速图像处理

## 总结

`vllm_bench` 成功扩展了MNN的LLM性能测试能力，增加了对图片提示词的完整支持。它保持了与原有工具的完全兼容性，同时为多模态LLM的性能评估提供了强大的工具支持。