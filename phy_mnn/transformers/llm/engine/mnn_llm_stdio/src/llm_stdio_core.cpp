//
//  llm_stdio_core.cpp
//
//  MNN LLM Stdio Backend - 基于三管道通信的LLM服务核心实现
//  支持OpenAI风格的结构化stderr消息和流式stdout输出
//  Author: MNN Development Team
//

#include "llm_stdio_core.hpp"
#include "llm/llm.hpp"
#define MNN_OPEN_TIME_TRACE
#include <MNN/AutoTime.hpp>
#include <MNN/expr/ExecutorScope.hpp>
#include <fstream>
#include <sstream>
#include <iostream>
#include <thread>
#include <chrono>

using namespace MNN::Transformer;

// 构造函数中初始化实例成员

LlmStdioCore::LlmStdioCore() : m_running(false), m_processing(false) {
    m_system_prompt = "";
    m_chat_history.clear();
}

LlmStdioCore::~LlmStdioCore() {
    stop();
}

bool LlmStdioCore::initialize(const std::string& config_path) {
    MNN::BackendConfig backendConfig;
    auto executor = MNN::Express::Executor::newExecutor(MNN_FORWARD_CPU, backendConfig, 1);
    MNN::Express::ExecutorScope s(executor);

    m_llm.reset(Llm::createLLM(config_path));
    if (!m_llm) {
        std::cerr << createStderrMessage("error", "error", "无法创建LLM实例") << std::endl;
        return false;
    }

    m_llm->set_config("{\"tmp_path\":\"tmp\"}");

    {
        AUTOTIME;
        bool res = m_llm->load();
        if (!res) {
            std::cerr << createStderrMessage("error", "error", "加载模型失败") << std::endl;
            return false;
        }
    }

    // 准备优化
    m_llm->tuning(OP_ENCODER_NUMBER, {1, 5, 10, 20, 30, 50, 100});

    // 设置为同步模式
    m_llm->set_config("{\"async\":false}");

    // 输出就绪状态
    std::cerr << createStderrMessage("status", "ready", "LLM已初始化并准备接收请求") << std::endl;
    std::cerr.flush();

    return true;
}

std::string LlmStdioCore::escapeJsonString(const std::string& input) {
    std::string escaped;
    for (char c : input) {
        switch (c) {
            case '"':
                escaped += "\\\"";
                break;
            case '\\':
                escaped += "\\\\";
                break;
            case '\b':
                escaped += "\\b";
                break;
            case '\f':
                escaped += "\\f";
                break;
            case '\n':
                escaped += "\\n";
                break;
            case '\r':
                escaped += "\\r";
                break;
            case '\t':
                escaped += "\\t";
                break;
            default:
                if (c < ' ' || c > 127) {
                    escaped += "\\u";
                    char hex[5];
                    sprintf(hex, "%04X", static_cast<unsigned char>(c));
                    escaped += hex;
                } else {
                    escaped += c;
                }
                break;
        }
    }
    return escaped;
}

std::string LlmStdioCore::createStderrMessage(const std::string& message_type,
                                                const std::string& status,
                                                const std::string& message,
                                                const std::string& response_text,
                                                const std::string& data) {
    std::string response = "{\"type\":\"" + escapeJsonString(message_type) + "\"";

    if (!status.empty()) {
        response += ",\"status\":\"" + escapeJsonString(status) + "\"";
    }

    if (!message.empty()) {
        response += ",\"message\":\"" + escapeJsonString(message) + "\"";
    }

    if (!response_text.empty()) {
        response += ",\"response\":\"" + escapeJsonString(response_text) + "\"";
    }

    if (!data.empty()) {
        response += ",\"data\":" + data;
    }

    // 添加时间戳
    auto now = std::chrono::system_clock::now();
    auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
    response += ",\"timestamp\":" + std::to_string(now_ms);

    response += "}";
    return response;
}

std::string LlmStdioCore::generateResponse(const std::string& id,
                                            const std::string& type,
                                            const std::string& content) {
    return "{\"id\":\"" + id + "\",\"type\":\"" + type + "\",\"content\":\"" + content + "\"}";
}

// 简单的JSON解析函数
std::string extractValue(const std::string& json_str, const std::string& key) {
    size_t key_pos = json_str.find("\"" + key + "\"");
    if (key_pos == std::string::npos) {
        return "";
    }

    size_t colon_pos = json_str.find(':', key_pos);
    if (colon_pos == std::string::npos) {
        return "";
    }

    size_t start_pos = colon_pos + 1;
    while (start_pos < json_str.size() && (json_str[start_pos] == ' ' || json_str[start_pos] == '\t')) {
        start_pos++;
    }

    // 处理字符串值
    if (json_str[start_pos] == '"') {
        start_pos++;
        size_t end_pos = json_str.find('"', start_pos);
        while (end_pos != std::string::npos && json_str[end_pos - 1] == '\\') {
            end_pos = json_str.find('"', end_pos + 1);
        }
        if (end_pos != std::string::npos) {
            return json_str.substr(start_pos, end_pos - start_pos);
        }
    }

    // 处理其他值
    size_t end_pos = start_pos;
    while (end_pos < json_str.size() && json_str[end_pos] != ',' && json_str[end_pos] != '}' && json_str[end_pos] != ']' && json_str[end_pos] != ' ') {
        end_pos++;
    }

    return json_str.substr(start_pos, end_pos - start_pos);
}

LlmStdioCore::Request LlmStdioCore::parseRequest(const std::string& request_str) {
    Request req;

    
    std::string type = extractValue(request_str, "type");
    req.method = type;
    req.id = extractValue(request_str, "id");

    if (type == "chat") {
        req.content = extractValue(request_str, "prompt");
        req.params["max_new_tokens"] = extractValue(request_str, "max_new_tokens");
    } else if (type == "system_prompt") {
        req.content = extractValue(request_str, "content");
    } else if (type == "reset") {
        // 重置请求不需要内容
    } else if (type == "status") {
        // 状态查询请求
    }

    return req;
}

// 流式输出缓冲区实现
LlmStdioCore::StreamingBuffer::StreamingBuffer(std::ostream& out_stream) : out(out_stream), started(false) {
}

void LlmStdioCore::StreamingBuffer::startStream() {
    if (!started) {
        out << "[LLM_STREAM_START]" << std::endl;
        out.flush();
        started = true;
    }
}

void LlmStdioCore::StreamingBuffer::endStream() {
    if (started) {
        out << "[LLM_STREAM_END]" << std::endl;
        out.flush();
        started = false;
    }
}

int LlmStdioCore::StreamingBuffer::overflow(int c) {
    if (c != EOF) {
        startStream();
        char buffer = static_cast<char>(c);
        out.write(&buffer, 1);
        out.flush();
    }
    return c;
}

std::streamsize LlmStdioCore::StreamingBuffer::xsputn(const char* s, std::streamsize n) {
    if (n > 0) {
        startStream();
        out.write(s, n);
        out.flush();
    }
    return n;
}

// 自定义捕获缓冲区
class CaptureBuffer : public std::streambuf {
public:
    CaptureBuffer(std::string& output) : output_(output) {}

protected:
    virtual std::streamsize xsputn(const char* s, std::streamsize n) override {
        output_.append(s, n);
        return n;
    }

    virtual int overflow(int c) override {
        if (c != EOF) {
            output_.push_back(static_cast<char>(c));
        }
        return c;
    }

private:
    std::string& output_;
};

void LlmStdioCore::handleSystemPromptRequest(const Request& req) {
    if (!req.content.empty()) {
        m_system_prompt = req.content;
        std::cerr << createStderrMessage("message", "success", "系统提示词设置成功") << std::endl;
        std::cerr.flush();
    } else {
        std::cerr << createStderrMessage("error", "error", "系统提示词内容为空") << std::endl;
        std::cerr.flush();
    }
}

void LlmStdioCore::handleResetRequest(const Request& req) {
    // 清空对话历史但保留系统提示词
    m_chat_history.clear();
    m_llm->reset();
    std::cerr << createStderrMessage("message", "success", "模型已重置，对话历史已清空，系统提示词保留") << std::endl;
    std::cerr.flush();
}

void LlmStdioCore::handleChatRequest(const Request& req) {
    m_processing = true;

    // 获取max_new_tokens参数
    int max_new_tokens = -1;
    auto max_tokens_it = req.params.find("max_new_tokens");
    if (max_tokens_it != req.params.end() && !max_tokens_it->second.empty()) {
        // 手动检查字符串是否为有效数字
        const std::string& str = max_tokens_it->second;
        bool valid = true;
        size_t i = 0;

        // 处理符号
        if (str[i] == '+' || str[i] == '-') {
            i++;
        }

        // 检查是否都是数字
        for (; i < str.size(); ++i) {
            if (!std::isdigit(str[i])) {
                valid = false;
                break;
            }
        }

        if (valid && !str.empty()) {
            max_new_tokens = std::stoi(str);
        }
    }

    // 创建流式输出缓冲区，输出到stdout
    StreamingBuffer streaming_buffer(std::cout);
    std::ostream streaming_os(&streaming_buffer);

    // 创建完整的消息列表
    ChatMessages messages;

    // 添加系统提示词
    if (!m_system_prompt.empty()) {
        messages.emplace_back("system", m_system_prompt);
    }

    // 添加对话历史
    messages.insert(messages.end(), m_chat_history.begin(), m_chat_history.end());

    // 添加新用户输入
    messages.emplace_back("user", req.content);

    // 捕获完整响应
    std::string full_response;
    CaptureBuffer capture_buffer(full_response);
    std::ostream capture_os(&capture_buffer);

    // 同时输出到stdout和捕获到缓冲区
    class TeeStream : public std::ostream {
    private:
        class TeeBuffer : public std::streambuf {
        private:
            std::streambuf* sb1;
            std::streambuf* sb2;
        public:
            TeeBuffer(std::streambuf* sb1, std::streambuf* sb2) : sb1(sb1), sb2(sb2) {}
            virtual int overflow(int c) override {
                if (c != EOF) {
                    sb1->sputc(c);
                    sb2->sputc(c);
                }
                return c;
            }
            virtual std::streamsize xsputn(const char* s, std::streamsize n) override {
                sb1->sputn(s, n);
                sb2->sputn(s, n);
                return n;
            }
        } buffer;
    public:
        TeeStream(std::ostream& os1, std::ostream& os2) : std::ostream(&buffer), buffer(os1.rdbuf(), os2.rdbuf()) {}
    } tee_stream(streaming_os, capture_os);

    // 调用LLM生成响应
    m_llm->response(messages, &tee_stream, nullptr, max_new_tokens);

    // 确保所有输出都已刷新
    tee_stream.flush();
    streaming_os.flush();
    capture_os.flush();
    std::cout.flush();

    // 增加延迟时间，确保LLM完全生成完所有内容
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 标记流式输出结束
    streaming_buffer.endStream();

    // 将对话添加到历史
    m_chat_history.emplace_back("user", req.content);
    m_chat_history.emplace_back("assistant", full_response);

    // 输出完成状态消息到stderr
    std::cerr << createStderrMessage("status", "success", "流式输出完成") << std::endl;

    // 输出包含完整响应的消息到stderr
    std::cerr << createStderrMessage("response", "success", "完整响应已生成", full_response) << std::endl;
    std::cerr.flush();

    m_processing = false;
}

void LlmStdioCore::handleStatusRequest(const Request& req) {
    std::string status = m_processing ? "processing" : "idle";
    auto context = m_llm->getContext();

    std::string info = "status:" + status +
                      ",prompt_len:" + std::to_string(context->prompt_len) +
                      ",gen_seq_len:" + std::to_string(context->gen_seq_len) +
                      ",chat_history_count:" + std::to_string(m_chat_history.size());

    std::cerr << createStderrMessage("status", "info", info) << std::endl;
    std::cerr.flush();
}

void LlmStdioCore::run() {
    m_running = true;
    std::string request;

    while (m_running) {
        request.clear();

        // 从stdin读取请求
        std::getline(std::cin, request);

        if (request.empty() && std::cin.eof()) {
            break;
        }

        if (request.empty()) {
            continue;
        }

        Request req = parseRequest(request);

        if (req.method == "chat") {
            handleChatRequest(req);
        } else if (req.method == "status") {
            handleStatusRequest(req);
        } else if (req.method == "system_prompt") {
            handleSystemPromptRequest(req);
        } else if (req.method == "reset") {
            handleResetRequest(req);
        } else if (req.method == "exit") {
            break;
        } else {
            std::cerr << createStderrMessage("error", "error", "未知请求类型: " + req.method) << std::endl;
            std::cerr.flush();
        }
    }
}

void LlmStdioCore::stop() {
    m_running = false;
}