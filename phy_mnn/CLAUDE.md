# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MNN is a highly efficient, lightweight deep learning framework for inference and training. It's designed for mobile devices and embedded systems, supporting multiple hardware backends (CPU, GPU, NPU) and model formats (TensorFlow, ONNX, Caffe, TorchScript).

## Build System and Common Commands

### Primary Build System
MNN uses CMake as its primary build system. Key build configurations are in the root `CMakeLists.txt`.

### Build Commands

**Basic Linux Build:**
```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DMNN_BUILD_CONVERTER=ON -DMNN_BUILD_TOOLS=ON
make -j$(nproc)
```

**Android Build (using CI scripts):**
```bash
# For arm64-v8a
./ciscripts/build.sh arm_android_64

# For armeabi-v7a
./ciscripts/build.sh arm_android_32
```

**Common Build Options:**
- `MNN_BUILD_CONVERTER=ON` - Build model converter tools
- `MNN_BUILD_TOOLS=ON` - Build command-line tools
- `MNN_BUILD_TRAIN=ON` - Enable training framework
- `MNN_OPENCL=ON` - Enable OpenCL GPU backend
- `MNN_METAL=ON` - Enable Metal backend (iOS/macOS)
- `MNN_VULKAN=ON` - Enable Vulkan backend
- `MNN_CUDA=ON` - Enable CUDA backend
- `MNN_BUILD_QUANTOOLS=ON` - Build quantization tools
- `MNN_BUILD_TEST=ON` - Build test suite
- `MNN_BUILD_BENCHMARK=ON` - Build benchmark tools

### Testing
```bash
# Build tests with MNN_BUILD_TEST=ON
# Run from build directory
ctest --output-on-failure
```

### Model Conversion
```bash
# Convert models (after building converter)
./MNNConvert -f ONNX --modelFile model.onnx --MNNModel model.mnn
./MNNConvert -f TF --modelFile model.pb --MNNModel model.mnn
```

## High-Level Architecture

MNN follows a layered architecture with clear separation between core engine, backends, tools, and applications:

### Core Components

**Core Inference Engine (`source/core/`)**:
- `Interpreter` - Main entry point, manages model loading and sessions
- `Session` - Execution context with optimized memory management
- `Pipeline` - Execution pipeline with optimization passes
- `Backend` - Hardware abstraction interface

**Backend System (`source/backend/`)**:
- CPU backend with ARM/x86 assembly optimizations
- GPU backends: OpenCL, Metal, Vulkan, CUDA
- NPU backends: CoreML, HIAI, NNAPI
- Each backend implements the abstract `Backend` interface

**Express Module (`express/`)**:
- Dynamic computation graph execution
- Expression-based API for flexible model building
- Support for control flow and dynamic operations
- Alternative to static Interpreter-based execution

### Model Conversion Pipeline (`tools/converter/`)
Converts TensorFlow, ONNX, Caffe, and TorchScript models to optimized MNN format:
1. Parse source model format
2. Convert to MNN intermediate representation
3. Apply graph optimizations and operator fusion
4. Generate optimized MNN model files

### Specialized Modules

**Transformers (`transformers/`)**:
- `llm/` - Large Language Model runtime with optimization for LLM inference
- `diffusion/` - Stable diffusion model runtime support

**Tools (`tools/`)**:
- `converter/` - Model format conversion
- `cv/` - Computer vision utilities (OpenCV-like but lightweight)
- `train/` - Model training utilities
- `quantization/` - Model quantization and compression
- `audio/` - Audio processing utilities

### Key Architectural Patterns

**Multi-Backend Abstraction**:
- Unified `Backend` interface across all hardware types
- Runtime factory pattern for backend creation
- Configuration-driven backend selection with fallback mechanisms

**Memory Management**:
- Memory pooling and allocation optimization
- Mobile-focused memory efficiency
- AutoStorage for automatic resource cleanup

**Optimization Framework**:
- GeometryComputer for operation transformations
- Winograd convolution for performance optimization
- Extensive quantization support for memory/computation reduction

**Plugin Architecture**:
- Operator registry for custom operations
- Backend plugin interface for hardware extensions

## Development Workflow

1. **Model Development**: Use existing framework to convert models with MNNConvert
2. **Inference Integration**: Use `Interpreter` API for standard inference or `Express` API for dynamic models
3. **Backend Selection**: Configure appropriate backends via build flags
4. **Performance Optimization**: Use built-in profiling and optimization tools
5. **Application Development**: Leverage specialized modules for LLM/Diffusion use cases

## Important File Locations

- **Public Headers**: `include/MNN/` - Core API definitions
- **Model Schema**: `schema/current/` - FlatBuffer schema definitions
- **Backend Implementations**: `source/backend/*/` - Hardware-specific code
- **Test Suite**: `test/` - Comprehensive test coverage
- **Application Examples**: `apps/` - Real-world implementations

## Hardware Support Notes

MNN provides varying levels of support across architectures:
- Level S: Fully supported and optimized
- Level A: Works well
- Level B: Has bugs or not optimized
- Level C: Not supported

Check supported backends per target hardware before build configuration.
- 本项目已经禁用了异常处理，不要在新增加的文件中使用异常处理
- 本项目使用的cmake编译指令是 -DMNN_LOW_MEMORY=true -DMNN_BUILD_LLM=true -DMNN_SUPPORT_TRANSFORMER_FUSE=true -DMNN_OPENMP=true -DMNN_USE_THREAD_POOL=true -DMNN_BUILD_TOOLS=ON -DBUILD_MLS=true -DMNN_BUILD_OPENCV=ON -DMNN_IMGCODECS=ON
- 使用中文来撰写文档
- 使用14个线程进行构建
- 只在十分必要的地方使用emoji
- 我们处理的问题是mnn_llm_stdio这个目录下面的东西，不要随意修改MNN项目本身
- git提交信息中不要包含Claude Code相关的信息，在提交信息的最后可以明确使用以下句式说明AI参与：“AI助手支持: GLM-4.6-AWQ”
- 不要随意修改配置文件中与思考标签相关的配置