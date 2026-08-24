// ============================================================================
// baml_extracts/clients.baml
//
// LLM client roster for the BIEP Hackathon v3.
//
//  - "MiniMax"   : MiniMax-M3 via api.minimax.io  (primary, cloud)
//  - "Unsloth"   : unsloth/gemma-4-26B-A4B-it-GGUF via Ollama-compatible
//                  local server (http://localhost:11434/v1)
//  - "Vertex"    : Gemini 3.5 Flash via Vertex AI  (fallback, gov-cloud)
//  - "TestMock"  : deterministic stub for `baml-cli test`
//
// Plus 3 retry policies:  MiniMaxRetry (3x), UnslothRetry (2x), VertexRetry (1x)
//
// N.B. BAML client + retry_policy identifiers MUST be PascalCase
// (parser rule: identifier must start with an uppercase letter).
// ============================================================================

// ----------------------------------------------------------------------------
// Retry policies
// ----------------------------------------------------------------------------

retry_policy MiniMaxRetry {
  max_retries 3
  strategy {
    type "exponential_backoff"
    delay_ms 1000
    multiplier 2
    max_delay_ms 30000
  }
}

retry_policy UnslothRetry {
  max_retries 2
  strategy {
    type "constant_delay"
    delay_ms 2000
  }
}

retry_policy VertexRetry {
  max_retries 1
  strategy {
    type "constant_delay"
    delay_ms 500
  }
}

// ----------------------------------------------------------------------------
// Primary: MiniMax (cloud, OpenAI-compatible)
// ----------------------------------------------------------------------------

client<llm> MiniMax {
  provider "openai-generic"
  options {
    base_url env.MINIMAX_BASE_URL
    api_key  env.MINIMAX_API_KEY
    model    env.MINIMAX_MODEL
    temperature 0.2
    top_p 0.95
  }
  retry_policy MiniMaxRetry
}

// ----------------------------------------------------------------------------
// Local: Unsloth via OpenAI-compatible API (Ollama / llama.cpp)
// ----------------------------------------------------------------------------

client<llm> Unsloth {
  provider "openai-generic"
  options {
    base_url env.UNSLOTH_BASE_URL
    api_key  env.UNSLOTH_API_KEY
    model    env.UNSLOTH_MODEL
    temperature 0.1
    top_p 0.95
    // hint to the local server that low VRAM is OK
    extra_options {
      "num_ctx" "8192"
      "num_gpu" "1"
      "num_thread" "8"
    }
  }
  retry_policy UnslothRetry
}

// ----------------------------------------------------------------------------
// Fallback: Vertex AI Gemini 3.5 Flash
// ----------------------------------------------------------------------------

client<llm> Vertex {
  provider "vertex-ai"
  options {
    model       env.VERTEX_AI_MODEL
    credentials env.GOOGLE_APPLICATION_CREDENTIALS
    project     env.GOOGLE_CLOUD_PROJECT
    location    env.GOOGLE_CLOUD_LOCATION
    temperature 0.2
    top_p 0.95
  }
  retry_policy VertexRetry
}

// ----------------------------------------------------------------------------
// Test client (used by baml-cli test -- deterministic, no network)
// ----------------------------------------------------------------------------

client<llm> TestMock {
  provider "openai-generic"
  options {
    base_url "http://localhost:0"
    api_key  "test"
    model    "gpt-4o-mini"
  }
  retry_policy MiniMaxRetry
}