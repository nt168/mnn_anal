//
//  main.cpp
//  MNN LLM Stdio Backend - 后端主程序
//  提供基于三管道通信的LLM服务后端
//  stdin接收请求，stderr发送结构化消息，stdout流式输出
//

#include "llm_stdio_core.hpp"
#include <iostream>
#include <string>

int main(int argc, const char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " 配置文件.json" << std::endl;
        std::cerr << "MNN LLM Stdio Backend - 基于三管道通信的LLM服务后端" << std::endl;
        std::cerr << "stdin: JSON请求, stdout: 流式输出, stderr: 状态消息" << std::endl;
        return 1;
    }

    std::string config_path = argv[1];

    MNN::Transformer::LlmStdioCore core;

    if (!core.initialize(config_path)) {
        std::cerr << "错误: 无法初始化LLM核心服务" << std::endl;
        return 1;
    }

    core.run();
    return 0;
}