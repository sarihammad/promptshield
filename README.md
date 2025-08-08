# LLM Gateway API

A production-grade API gateway for LLM providers (OpenAI, Anthropic) with retry logic, cost control, rate limiting, caching, and comprehensive logging. Built with FastAPI and Redis for high-performance, scalable LLM API management.

---

## Architecture

```mermaid
graph TD
    %% Client Layer
    subgraph "Client Layer"
        A1["API Client"] -->|"HTTP/HTTPS"| A2["Load Balancer<br>(Optional)"]
        A2 -->|"Rate Limited"| A3["API Gateway<br>(FastAPI)"]
    end

    %% Gateway Layer
    subgraph "Gateway Layer (FastAPI)"
        B1["Request Validation<br>(Pydantic)"] -->|"Validated Request"| B2["Rate Limiter<br>(Redis)"]
        B2 -->|"Rate Check"| B3["Cache Check<br>(Redis)"]
        B3 -->|"Cache Hit/Miss"| B4["Retry Handler<br>(Exponential Backoff)"]
        B4 -->|"LLM Request"| B5["Cost Tracker<br>(Token Usage)"]
        B5 -->|"Response"| B6["Response Formatter<br>(JSON)"]
    end

    %% Provider Layer
    subgraph "Provider Layer"
        C1["OpenAI Client<br>(GPT-4, GPT-3.5)"] -->|"API Calls"| C2["OpenAI API"]
        C3["Anthropic Client<br>(Claude Models)"] -->|"API Calls"| C4["Anthropic API"]
    end

    %% Data Layer
    subgraph "Data Layer"
        D1["Redis<br>(Cache & Rate Limiting)"] -->|"Cache Storage"| D2["Response Cache"]
        D1 -->|"Rate Tracking"| D3["User Rate Limits"]
        D4["Logging System<br>(Structured JSON)"] -->|"Event Logs"| D5["Cost Logs"]
        D4 -->|"Performance Logs"| D6["Request Logs"]
    end

    %% Monitoring Layer
    subgraph "Monitoring Layer"
        E1["Health Checks<br>(/health)"] -->|"System Status"| E2["Metrics Dashboard"]
        E3["Admin Endpoints<br>(/admin)"] -->|"Usage Statistics"| E4["Cost Monitoring"]
        E5["Cache Statistics<br>(/cache)"] -->|"Cache Metrics"| E6["Performance Monitoring"]
    end

    %% Cross-layer connections
    A3 -->|"API Requests"| B1
    B4 -->|"Provider Selection"| C1
    B4 -->|"Provider Selection"| C3
    B3 -->|"Cache Operations"| D1
    B2 -->|"Rate Limit Check"| D1
    B5 -->|"Cost Tracking"| D4
    B6 -->|"Response"| A3
    C2 -->|"LLM Response"| B4
    C4 -->|"LLM Response"| B4
```

---

## System Overview

LLM Gateway API implements a robust, production-ready architecture with comprehensive error handling, cost control, and observability across five main layers:

### **Client Layer**

- **API Clients**: RESTful HTTP clients with proper authentication and rate limiting
- **Load Balancing**: Optional load balancer for horizontal scaling
- **Request Validation**: Automatic input validation and sanitization
- **Response Formatting**: Consistent JSON responses with metadata

### **Gateway Layer**

- **Request Processing**: FastAPI-based request handling with Pydantic validation
- **Rate Limiting**: Per-user rate limiting with sliding window implementation
- **Caching**: Redis-based response caching to reduce API calls and costs
- **Retry Logic**: Exponential backoff with jitter for transient failures
- **Cost Tracking**: Real-time token usage and cost monitoring
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

### **Provider Layer**

- **Multi-Provider Support**: Unified interface for OpenAI and Anthropic APIs
- **Model Routing**: Automatic routing based on model selection
- **Provider Fallback**: Graceful handling of provider-specific errors
- **Token Estimation**: Accurate token counting and cost calculation

### **Data Layer**

- **Redis Cache**: High-performance caching for LLM responses
- **Rate Limit Storage**: Distributed rate limiting with Redis
- **Structured Logging**: JSON-formatted logs for observability
- **Cost Tracking**: Persistent cost and usage statistics

### **Monitoring Layer**

- **Health Checks**: Comprehensive system health monitoring
- **Admin Dashboard**: Usage statistics and cost monitoring
- **Performance Metrics**: Response times and cache hit rates
- **Error Tracking**: Detailed error logging and alerting

The system supports multiple user types:

1. **API Consumers**: External applications making LLM requests
2. **Admin Users**: System administrators monitoring usage and costs
3. **Monitoring Systems**: Health checks and metrics collection

---

## Data Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant R as Redis
    participant O as OpenAI
    participant A as Anthropic
    participant L as Logger

    %% Request Processing
    C->>G: POST /v1/generate
    G->>G: Validate request (Pydantic)
    G->>L: Log incoming request

    %% Cache Check
    G->>R: Check cache for prompt
    alt Cache Hit
        R-->>G: Cached response
        G->>L: Log cache hit
        G-->>C: Return cached response
    else Cache Miss
        %% Rate Limiting
        G->>R: Check rate limits
        R-->>G: Rate limit status

        %% Provider Selection
        G->>G: Select provider (OpenAI/Anthropic)

        %% Retry Logic
        loop Retry with backoff
            alt OpenAI Request
                G->>O: API call with retry
                O-->>G: Response with tokens
            else Anthropic Request
                G->>A: API call with retry
                A-->>G: Response with tokens
            end
        end

        %% Cost Tracking
        G->>G: Calculate cost from tokens
        G->>L: Log cost and usage

        %% Caching
        G->>R: Cache response
        G->>L: Log response

        %% Response
        G-->>C: Formatted response
    end

    %% Monitoring
    G->>L: Log final metrics
    L->>L: Structured JSON logging
```

---

## Features

### **Core Functionality**

- **Multi-Provider Support**: Unified interface for OpenAI (GPT-4, GPT-3.5) and Anthropic (Claude) APIs
- **Intelligent Retry Logic**: Exponential backoff with jitter for transient failures
- **Advanced Rate Limiting**: Per-user rate limiting with sliding window implementation
- **Cost Control**: Real-time token usage tracking and cost monitoring
- **Response Caching**: Redis-based caching to reduce API calls and improve performance

### **Production Features**

- **Structured Logging**: JSON-formatted logs with comprehensive request/response tracking
- **Health Monitoring**: Comprehensive health checks with Redis connectivity testing
- **Admin Dashboard**: Usage statistics, cost monitoring, and system metrics
- **Error Handling**: Graceful error handling with proper HTTP status codes
- **Security**: Input validation, rate limiting, and secure error responses

### **Scalability & Performance**

- **Horizontal Scaling**: Stateless design allows multiple instances behind load balancer
- **Redis Integration**: Distributed caching and rate limiting
- **Async Processing**: Non-blocking request handling with FastAPI
- **Performance Metrics**: Response time tracking and cache hit rate monitoring

### **Developer Experience**

- **Interactive Documentation**: Auto-generated API docs with OpenAPI/Swagger
- **Type Safety**: Full Pydantic validation for all requests and responses
- **Comprehensive Testing**: Unit and integration tests with mocking
- **Docker Support**: Production-ready containerization with health checks

### **Monitoring & Observability**

- **Request Tracking**: Unique request IDs for end-to-end tracing
- **Cost Analytics**: Per-user and per-model cost breakdown
- **Performance Metrics**: Latency tracking and cache statistics
- **Error Monitoring**: Detailed error logging with context
