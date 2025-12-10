# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The `mnn_llm_bench` repository is designed to comprehensively benchmark and analyze the performance characteristics of MNN (Mobile Neural Network) LLM inference framework. The project uses MNN's built-in benchmarking tool to evaluate various performance metrics across different models, configurations, and scenarios.

## Project Purpose

This repository conducts systematic performance research on MNN LLM inference to establish performance baselines, identify optimization opportunities, and provide deployment recommendations for mobile and edge environments.

## MNN Architecture Insights

Based on analysis of the `reference/llm` source code, MNN's LLM engine features several key architectural components:

### Core Design Patterns

#### 1. Module Pool Architecture
- **Prefill Module Pool**: Shared modules for input preprocessing (fixed key=100)
- **Dynamic Module Creation**: Generate hashing modules on-demand based on sequence length
- **Memory Reuse**: Module pools reduce allocation overhead significantly

#### 2. KV Cache Management
- **Conditional Caching**: Controlled via `-kv` parameter (true/false)
- **Cache Efficiency**: Greatly accelerates generation but increases memory usage
- **History Management**: LlmContext tracks cached state with dynamic cleanup

#### 3. Dual-Phase Inference
```cpp
// LlmContext timing structure
struct LlmContext {
    int64_t prefill_us;    // Parallel input processing
    int64_t decode_us;     // Sequential token generation
    int64_t sample_us;     // Sampling algorithm time
    // ... other timing metrics
};
```

#### 4. Multi-Backend Abstraction
- **Backend Mapping**: 0=CPU, 1=METAL, 3=OPENCL
- **Runtime Configuration**: JSON-driven backend switching
- **Executor Management**: Separate runtime managers per backend type

### Sampling Optimization

#### SubsetLogits Mechanism
- **Memory Efficiency**: Reduces memory copying during sampling
- **Parallel Processing**: SIMD-optimized logits transformation
- **Mixed Sampling**: penalty + topK + topP + min_p + temperature strategies

#### Sampling Algorithms
The sampler supports multiple strategies:
- Top-K and Top-P selection
- Min-P filtering
- Temperature scaling
- Repetition penalty
- Mixed sampler combinations

### Performance Optimization levers

#### Dynamic Optimization (`-dyo`)
- **Level 0**: Conservative resource usage
- **Level 8**: Performance-first (uses more memory for better decode performance)
- Implementation: Memory layout optimization and computation strategy adjustment

#### Precision Hierarchy
- **Low (2)**: Fast computation with accuracy trade-off
- **Normal (0)**: CPU default backend setting
- **High (1)**: Quality-focused computation

#### Memory Mapping (`-mmp`)
- **Traditional Load**: Complete model in memory
- **Memory-Mapped**: Lazy loading reduces initial footprint
- Use case: Large model deployments

## Available Resources

### MNN Benchmark Tool
- **Location**: `~/mnn/build/llm_bench`
- **Type**: Executable binary compiled from MNN source
- **Purpose**: LLM inference benchmarking and performance measurement

### Available Models
- **Location**: `~/models/`
- **Models Available**:
  - Qwen3-0.6B-MNN (0.6B parameters)
  - Qwen3-VL-2B/4B/8B-Instruct-MNN (2B/4B/8B multimodal)
  - DeepSeek-R1-1.5B/7B-Qwen-MNN (1.5B/7B reasoning enhanced)
- **Model Structure**: Each model directory contains:
  - `config.json`: MNN-specific runtime configuration
  - `llm.mnn`: Main model weights
  - `llm.mnn.weight`: Additional weight files
  - `tokenizer.txt`: Tokenizer vocabulary
  - `llm_config.json`: Model architecture configuration

## Common Development Commands

### Basic Benchmarks
```bash
# Basic benchmark run
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json

# Multiple runs for statistical significance
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -rep 5
```

### Performance Comparison Tests
```bash
# Different thread counts
for threads in 1 2 4 8; do
  ~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -t $threads -rep 3
done

# Different precision modes
for precision in 0 1 2; do
  ~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -c $precision -rep 3
done

# Different sequence lengths
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -p 512 -n 128 -rep 3
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -p 2048 -n 512 -rep 2
```

### Advanced Features
```bash
# KV Cache impact test
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -kv true -rep 3
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -kv false -rep 3

# Memory mapping test
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -mmp 1 -rep 3

# Different backends (if supported)
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -a opencl -rep 3
```

### Batch Testing
```bash
# Test all Qwen3-VL models
for model in Qwen3-VL-2B-Instruct-MNN Qwen3-VL-4B-Instruct-MNN Qwen3-VL-8B-Instruct-MNN; do
  echo "Testing $model..."
  ~/mnn/build/llm_bench -m ~/models/$model/config.json -rep 3
done
```

## Key Parameters and Their Effects

### Performance Parameters
- `-t, --threads`: Critical for performance. Start with physical core count, test 1-16 range
- `-c, --precision`: 2=Low (fastest), 1=High, 0=Normal. Lower precision = faster but less accurate
- `-p, --n-prompt`: Input sequence length. Longer sequences require more memory
- `-n, --n-gen`: Output sequence length. Affects total inference time
- `-kv, --kv-cache`: Enables caching for faster generation but uses more memory

### Output Parameters
- `-rep, --n-repeat`: Number of iterations for statistical reliability
- `-fp, --file-print`: Output destination (stdout or file for analysis)
- `-load, --loading-time`: Measure model loading time

## Architecture Overview

The testing methodology follows a systematic approach:

1. **Baseline Establishment**: Use lightest model (0.6B) to establish baseline metrics
2. **Parameter Sweeps**: Systematically vary key parameters to find optimal configurations
3. **Model Scaling**: Test across parameter scales (0.6B, 2B, 4B, 8B) to understand scaling behavior
4. **Feature Analysis**: Isolate impact of specific features (KV cache, precision, memory mapping)
5. **Comparative Studies**: Compare model families and architectures

## Performance Metrics Priority

1. **Throughput**: tokens/second generation rate
2. **Latency**: Time to first token and generation time
3. **Memory Efficiency**: Peak memory usage per token throughput
4. **Scalability**: Performance scaling with threads and model size
5. **Consistency**: Variability across multiple runs

## Additional Testing Commands

### System Monitoring During Tests
```bash
# Monitor memory and CPU during benchmark
htop &
~/mnn/build/llm_bench -m ~/models/Qwen3-0.6B-MNN/config.json -rep 5

# Check system resources before/after
free -h
nproc
```

### Results Collection
```bash
# Create structured result directories
mkdir -p results/{basic,scaling,advanced}

# Run with structured output naming
model=Qwen3-0.6B-MNN
~/mnn/build/llm_bench -m ~/models/$model/config.json -rep 5 \
  -fp results/basic/${model}_baseline.csv
```

## Development Guidelines

- Always start with Qwen3-0.6B-MNN for quick validation of configuration changes
- Use at least 3 repetitions for statistical reliability
- Monitor system resources during tests to identify bottlenecks
- Document any anomalies or unexpected behavior in results
- When testing with different parameters, change only one variable at a time
- For large models (4B+), be prepared for longer run times and higher memory usage

### Architecture-Specific Guidelines

#### 1. Test Standards Selection
- Use `llama.cpp` mode (`-kv false`) for official benchmark comparisons
- Use `llm_demo` mode (`-kv true`) for real-world performance evaluation
- Choose based on your target deployment scenario

#### 2. Performance Tuning Priority
1. **First**: Enable KV cache (`-kv true`) for continuous generation
2. **Second**: Set dynamic optimization (`-dyo 8`)
3. **Third**: Optimize threads (`-t`) to match physical cores
4. **Fourth**: Choose precision (`-c`) based on quality requirements
5. **Fifth**: Consider memory mapping (`-mmp 1`) for large models

#### 3. Configuration Validation
When encountering `set_config` errors:
- Check model's original config.json for conflicting settings
- Apply configuration incrementally to isolate conflicts
- Verify model family compatibility (Qwen vs DeepSeek vs LLaMA)
- Refer to `reference/llm/engine/src/llmconfig.cpp` for configuration resolution

#### 4. Memory Management
- Monitor memory usage with KV cache enabled/disabled
- Use memory mapping for models > 2B parameters
- Consider precision impact on memory footprint
- Track module pool effectiveness for repeated operations

#### 5. Backend-Specific Optimization
- **CPU**: Focus on thread optimization and precision tuning
- **OpenCL**: Verify GPU driver compatibility and memory limits
- **Metal**: Ensure macOS-specific optimizations are utilized

### Code Architecture Insights

#### Critical File Locations
- `reference/llm/engine/include/llm/llm.hpp`: Core API interfaces
- `reference/llm/engine/src/llm.cpp`: Main implementation logic
- `reference/llm/engine/src/sampler.cpp`: Sampling algorithm implementation
- `reference/llm/engine/src/llmconfig.cpp`: Configuration management
- `reference/llm/engine/demo/llm_bench.cpp`: Benchmark tool implementation

#### Performance Measurement Points
```cpp
// Key timing metrics in LlmContext
- load_us: Model loading duration
- prefill_us: Input preprocessing phase
- decode_us: Token generation phase
- sample_us: Sampling algorithm duration
```

#### Module Pool Keys
- Prefill key fixed at 100 for shared module reuse
- Dynamic modules keyed by sequence length
- Module pool hits significantly reduce initialization overhead

## Troubleshooting Common Issues

- 使用中文撰写文档，仅在非常必要的情况下使用emoji
- git提交信息中严禁包含Claude Code相关的信息，在提交信息的最后可以明确使用以下句式说明AI助手的参与：“AI助手支持: GLM-4.6-AWQ”
- 禁止采用删除文件重写一个简洁版的方法来修改长文件
- 很长的pp和tg非常浪费测试时间，过多的重复测试次数也是如此。调试过程中不要使用大于64的pp和tg值,不要使用多于2次的重复
- 使用uv管理本系统,使用uv run来执行必要的命令
- git 提交后立即推送到远程