//
//  llm_chat_tool.cpp
//
//  Created for MNN LLM Streaming Chat Tool
//  Advanced CLI tool for streaming LLM inference with token analysis using MNN LLM backend
//

#include "llm/llm.hpp"
#include <MNN/expr/ExecutorScope.hpp>
#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <vector>

using namespace MNN::Transformer;

void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " <config.json> [options]" << std::endl;
    std::cout << "Interactive mode:          " << program_name << " <config.json>" << std::endl;
    std::cout << "Direct text:               " << program_name << " <config.json> \"your prompt here\"" << std::endl;
    std::cout << "File input:                " << program_name << " <config.json> -f prompt.txt" << std::endl;
    std::cout << "Default: Streaming LLM Chat with token analysis" << std::endl;
    std::cout << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  -t, --token-only  Analyze tokens ONLY, skip LLM inference" << std::endl;
    std::cout << "  -f, --file <path> Read prompt from file" << std::endl;
    std::cout << "  -v, --verbose     Show detailed token-by-token breakdown" << std::endl;
    std::cout << "  -m, --max-tokens <num> Max new tokens to generate (default: 100)" << std::endl;
    std::cout << "  -h, --help        Show this help message" << std::endl;
    std::cout << std::endl;
    std::cout << "Examples:" << std::endl;
    std::cout << "  " << program_name << " config.json \"Hello, how are you?\"" << std::endl;
    std::cout << "  " << program_name << " config.json -t -f prompt.txt" << std::endl;
    std::cout << "  " << program_name << " config.json -v -m 200 \"写一个科幻故事\"" << std::endl;
}

int main(int argc, const char* argv[]) {
    // Handle help argument first
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            return 0;
        }
    }

    // Parse command line arguments
    bool verbose_mode = false;         // Show detailed token breakdown
    bool file_mode = false;
    bool token_only_mode = false;      // Skip LLM inference
    int max_new_tokens = 100;          // Max new tokens to generate
    std::string input_text;
    std::string file_path;

    for (int i = 2; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "-t" || arg == "--token-only") {
            token_only_mode = true;
        } else if (arg == "-v" || arg == "--verbose") {
            verbose_mode = true;
        } else if (arg == "-m" || arg == "--max-tokens") {
            if (i + 1 < argc) {
                max_new_tokens = std::atoi(argv[++i]);
                if (max_new_tokens < 1) {
                    std::cerr << "Error: max-tokens must be a positive number" << std::endl;
                    return 1;
                }
            } else {
                std::cerr << "Error: --max-tokens option requires a number" << std::endl;
                print_usage(argv[0]);
                return 1;
            }
        } else if (arg == "-f" || arg == "--file") {
            file_mode = true;
            if (i + 1 < argc) {
                file_path = argv[++i];
            } else {
                std::cerr << "Error: --file option requires a file path" << std::endl;
                print_usage(argv[0]);
                return 1;
            }
        } else if (arg[0] != '-') {
            if (file_mode) {
                // This should not happen due to the logic above
                continue;
            } else {
                input_text = arg;
            }
        } else {
            std::cerr << "Error: Unknown option: " << arg << std::endl;
            print_usage(argv[0]);
            return 1;
        }
    }

    // Check arguments
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    // Init MNN environment
    MNN::BackendConfig backendConfig;
    auto executor = MNN::Express::Executor::newExecutor(MNN_FORWARD_CPU, backendConfig, 1);
    MNN::Express::ExecutorScope s(executor);

    std::string config_path = argv[1];
    std::cout << "Loading LLM with config: " << config_path << std::endl;

    // Create and load LLM
    std::unique_ptr<Llm> llm(Llm::createLLM(config_path));
    if (!llm) {
        std::cerr << "Error: Failed to create LLM" << std::endl;
        return 1;
    }

    llm->set_config("{\"tmp_path\":\"tmp\"}");
    {
        bool res = llm->load();
        if (!res) {
            std::cerr << "Error: Failed to load LLM" << std::endl;
            return 1;
        }
    }

    // Perform performance optimization (silent)
    llm->tuning(OP_ENCODER_NUMBER, {1, 5, 10, 20, 30, 50, 100});

    std::cout << "LLM loaded and optimized successfully!" << std::endl;

    // Get input text
    std::string text_to_tokenize;

    if (file_mode) {
        // Read from file
        std::ifstream file(file_path);
        if (!file.is_open()) {
            std::cerr << "Error: Cannot open file: " << file_path << std::endl;
            return 1;
        }
        std:: stringstream buffer;
        buffer << file.rdbuf();
        text_to_tokenize = buffer.str();
        std::cout << "Reading from file: " << file_path << std::endl;
    } else if (!input_text.empty()) {
        // Direct argument mode
        text_to_tokenize = input_text;
        std::cout << "Text from command line: " << text_to_tokenize << std::endl;
    } else {
        // Interactive mode
        std::cout << "Enter text to tokenize (Ctrl+D to exit):" << std::endl;
        std::cout << "> ";
        std::getline(std::cin, text_to_tokenize);
    }

    if (text_to_tokenize.empty()) {
        std::cout << "No input text provided. Exiting." << std::endl;
        return 0;
    }

    // Tokenize (verbose mode only)
    auto tokens = llm->tokenizer_encode(text_to_tokenize);

    // Detailed token analysis (verbose mode only)
    if (verbose_mode) {
        std::cout << "\n--- Token Analysis (Verbose) ---" << std::endl;
        std::cout << "Prompt: \"" << text_to_tokenize << "\"" << std::endl;
        std::cout << "Token count: " << tokens.size() << std::endl;

        // Print token array
        std::cout << "Token array: [";
        for (size_t i = 0; i < tokens.size(); i++) {
            if (i > 0) std::cout << ", ";
            std::cout << tokens[i];
        }
        std::cout << "]" << std::endl;

        std::cout << "\n--- Detailed Token Breakdown ---" << std::endl;
        std::cout << "Index\tToken\t\tDecoded Text\t\tUTF-8 Chars" << std::endl;
        std::cout << "-----\t-----\t\t-----------\t\t-----------" << std::endl;

        int total_char_count = 0;
        for (size_t i = 0; i < tokens.size(); i++) {
            std::string decoded_token = llm->tokenizer_decode(tokens[i]);
            int char_count = decoded_token.length();
            total_char_count += char_count;

            std::cout << i << "\t" << tokens[i] << "\t\t";
            // Sanitize output for printing
            bool needs_quotes = (decoded_token.find_first_of(" \t\n\r\"\\") != std::string::npos);
            if (needs_quotes) {
                std::cout << "\"";
            }
            // Print non-printable chars as hex codes
            for (char c : decoded_token) {
                if (c >= 32 && c <= 126) {
                    std::cout << c;
                } else {
                    printf("\\x%02x", (unsigned char)c);
                }
            }
            if (needs_quotes) {
                std::cout << "\"";
            }
            std::cout << "\t\t" << char_count << std::endl;
        }
        std::cout << "Total UTF-8 characters: " << total_char_count << std::endl;
    }

    // Token-only mode: don't do LLM inference
    if (token_only_mode) {
        std::cout << "\n--- Token-Only Mode (No LLM Inference) ---" << std::endl;
        std::cout << "Use default mode to see LLM inference results." << std::endl;
        return 0;
    }

    // LLM Inference with streaming output
    std::cout << "\n--- LLM Streaming Response ---\n";
    std::cout << "====================\n";

    // Run LLM inference with direct streaming output
    llm->response(text_to_tokenize, &std::cout, nullptr, max_new_tokens);

    std::cout << "\n====================\n";

    // Get final response for analysis
    auto context = llm->getContext();
    std::stringstream llm_output;
    for (int token : context->output_tokens) {
        llm_output << llm->tokenizer_decode(token);
    }
    std::string llm_response = llm_output.str();

    std::cout << "\n--- Inference Statistics ---" << std::endl;
    std::cout << "Prompt tokens: " << context->prompt_len << std::endl;
    std::cout << "Generated tokens: " << context->gen_seq_len << std::endl;
    std::cout << "Total tokens processed: " << context->all_seq_len << std::endl;

    if (context->prefill_us > 0) {
        std::cout << "Prefill time: " << (context->prefill_us / 1000.0) << " ms" << std::endl;
        std::cout << "Prefill speed: " << (context->prompt_len * 1000000.0 / context->prefill_us) << " tokens/sec" << std::endl;
    }
    if (context->decode_us > 0) {
        std::cout << "Decode time: " << (context->decode_us / 1000.0) << " ms" << std::endl;
        std::cout << "Decode speed: " << (context->gen_seq_len * 1000000.0 / context->decode_us) << " tokens/sec" << std::endl;
    }

    // Show generated tokens in verbose mode
    if (verbose_mode && !context->output_tokens.empty()) {
        std::cout << "\n--- Generated Tokens ---" << std::endl;
        for (size_t i = 0; i < context->output_tokens.size(); i++) {
            int token = context->output_tokens[i];
            std::string decoded_token = llm->tokenizer_decode(token);
            std::cout << "[" << i << "] Token " << token << " → \"" << decoded_token << "\"" << std::endl;
        }
    }

    
    return 0;
}