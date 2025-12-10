//
//  llm_stdio_core.hpp
//
//  MNN LLM Stdio Backend - 基于三管道通信的LLM服务核心接口
//  Author: MNN Development Team
//

#ifndef LLM_STDIO_CORE_HPP
#define LLM_STDIO_CORE_HPP

#include <string>
#include <memory>
#include <atomic>
#include <unordered_map>
#include <iostream>
#include <vector>
#include <thread>

namespace MNN {
namespace Transformer {

// 类型定义
using ChatMessage = std::pair<std::string, std::string>; // <role, content>
using ChatMessages = std::vector<ChatMessage>;

/**
 * @brief 标准输入输出LLM服务核心类
 *
 * LlmStdioCore 提供一个轻量级的LLM服务接口，通过stdin/stdout/stderr进行通信。
 * 主要特点：
 * - JSON协议通信
 * - 支持对话、状态查询、系统提示词设置、重置、优雅退出
 * - 线程安全的状态管理
 * - 兼容MNN LLM架构
 * - 流式stdout输出，结构化stderr消息（OpenAI风格）
 */
class LlmStdioCore {
private:
    std::unique_ptr<class Llm> m_llm;      // LLM实例
    std::atomic<bool> m_running;            // 运行状态
    std::atomic<bool> m_processing;         // 处理状态

    /**
     * @brief 请求数据结构
     */
    struct Request {
        std::string id;                     // 请求ID
        std::string method;                 // 请求方法 (chat/status/system_prompt/reset/exit)
        std::string content;                // 请求内容
        std::unordered_map<std::string, std::string> params;  // 额外参数
    };

public:
    /**
     * @brief 构造函数
     */
    LlmStdioCore();

    /**
     * @brief 析构函数
     */
    ~LlmStdioCore();

    /**
     * @brief 初始化LLM服务
     * @param config_path 配置文件路径
     * @return 初始化是否成功
     */
    bool initialize(const std::string& config_path);

    /**
     * @brief 解析JSON格式的请求
     * @param request_str 请求字符串
     * @return 解析后的请求对象
     */
    Request parseRequest(const std::string& request_str);

    /**
     * @brief 生成JSON格式的响应（兼容旧版本）
     * @param id 请求ID
     * @param type 响应类型 (start/complete/error/status)
     * @param content 响应内容
     * @return JSON格式的响应字符串
     */
    std::string generateResponse(const std::string& id,
                                const std::string& type,
                                const std::string& content);

    /**
     * @brief 生成OpenAI风格的结构化stderr消息
     * @param message_type 消息类型 (status/error/log/message/response)
     * @param status 状态 (success/error/ready/info)
     * @param message 文本信息
     * @param response_text 完整响应内容（可选）
     * @param data 额外数据（可选）
     * @return JSON格式的stderr消息字符串
     */
    std::string createStderrMessage(const std::string& message_type,
                                    const std::string& status = "",
                                    const std::string& message = "",
                                    const std::string& response_text = "",
                                    const std::string& data = "");

    /**
     * @brief JSON字符串转义函数
     * @param input 输入字符串
     * @return 转义后的JSON安全字符串
     */
    std::string escapeJsonString(const std::string& input);

    /**
     * @brief 处理聊天请求
     * @param req 聊天请求对象
     */
    void handleChatRequest(const Request& req);

    /**
     * @brief 处理状态查询请求
     * @param req 状态请求对象
     */
    void handleStatusRequest(const Request& req);

    /**
     * @brief 处理系统提示词设置请求
     * @param req 系统提示词请求对象
     */
    void handleSystemPromptRequest(const Request& req);

    /**
     * @brief 处理重置请求
     * @param req 重置请求对象
     */
    void handleResetRequest(const Request& req);

    /**
     * @brief 流式输出缓冲区类 - 用于stdout的token流式输出
     */
    class StreamingBuffer : public std::streambuf {
    public:
        StreamingBuffer(std::ostream& out_stream);

        void startStream();
        void endStream();

    protected:
        virtual int overflow(int c) override;
        virtual std::streamsize xsputn(const char* s, std::streamsize n) override;

    private:
        std::ostream& out;
        bool started;
    };

    /**
     * @brief 运行服务主循环
     * 从stdin读取请求，处理后输出到stdout/stderr
     */
    void run();

    /**
     * @brief 停止服务
     */
    void stop();

private:
    std::string m_system_prompt;  // 全局系统提示词
    ChatMessages m_chat_history;  // 对话历史
};

} // namespace Transformer
} // namespace MNN

#endif // LLM_STDIO_CORE_HPP