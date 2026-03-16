# API & Programmatic Integration Guide

## Overview

Memento provides multiple programmatic integration options for developers who need to access memory capabilities from custom applications, scripts, or services. This guide covers all API-based integration methods beyond the standard MCP protocol.

### When to Use Programmatic APIs

| Use Case | Recommended API | Why |
|----------|----------------|-----|
| Web applications | HTTP REST API | Standard HTTP, language-agnostic |
| Node.js/JavaScript apps | Node.js SDK | Native JavaScript integration |
| Python scripts/services | Python API | Direct Python integration |
| Containerized deployment | Docker API | Consistent environment, easy scaling |
| Cross-language systems | HTTP REST API | Universal compatibility |
| CLI tools/automation | Python API or Node.js SDK | Scripting-friendly |

## HTTP REST API

### Overview
The HTTP REST API provides a FastAPI-based wrapper around Memento, exposing memory operations as standard HTTP endpoints. This is ideal for web applications, microservices, or any system that needs to access memories over HTTP.

### Quick Start

1. **Create the HTTP wrapper** (`memento-http.py`):
```python
#!/usr/bin/env python3
"""
memento-http.py - HTTP API wrapper for Memento
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from memento import Memento

app = FastAPI(title="Memento HTTP API")
server = None

class MemoryCreate(BaseModel):
    type: str
    title: str
    content: str
    tags: Optional[List[str]] = None
    importance: float = 0.5

class SearchQuery(BaseModel):
    query: str
    limit: int = 20
    memory_types: Optional[List[str]] = None

@app.on_event("startup")
async def startup_event():
    """Initialize Memento server on startup."""
    global server
    server = Memento()
    await server.initialize()
    print("Memento HTTP server started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if server:
        await server.cleanup()

@app.post("/memories")
async def create_memory(memory: MemoryCreate):
    """Create a new memory."""
    try:
        memory_id = await server.store_memory(
            type=memory.type,
            title=memory.title,
            content=memory.content,
            tags=memory.tags or [],
            importance=memory.importance
        )
        return {"id": memory_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories/{memory_id}")
async def get_memory(memory_id: str):
    """Get a specific memory."""
    try:
        memory = await server.get_memory(memory_id)
        return {
            "id": memory.id,
            "type": memory.type,
            "title": memory.title,
            "content": memory.content,
            "tags": memory.tags,
            "importance": memory.importance,
            "confidence": memory.confidence
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/search")
async def search_memories(query: SearchQuery):
    """Search memories."""
    try:
        results = await server.recall_memories(
            query=query.query,
            limit=query.limit,
            memory_types=query.memory_types
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics")
async def get_stats():
    """Get database statistics."""
    try:
        stats = await server.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

2. **Install dependencies**:
```bash
pip install fastapi uvicorn mcp-memento
```

3. **Run the server**:
```bash
python memento-http.py
```

### API Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/memories` | Create new memory | `MemoryCreate` | `{"id": "mem-123", "status": "created"}` |
| GET | `/memories/{id}` | Get memory by ID | - | `Memory` object |
| POST | `/search` | Search memories | `SearchQuery` | `{"results": [...], "count": N}` |
| GET | `/statistics` | Get system stats | - | Statistics object |
| GET | `/health` | Health check | - | `{"status": "healthy"}` |

### Usage Examples

#### Using curl:
```bash
# Store a memory
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "type": "solution",
    "title": "API Rate Limiting",
    "content": "Implemented token bucket algorithm",
    "tags": ["api", "security"],
    "importance": 0.8
  }'

# Search memories
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "rate limiting", "limit": 5}'

# Get memory by ID
curl http://localhost:8000/memories/mem-abc123

# Get statistics
curl http://localhost:8000/statistics
```

#### Using Python requests:
```python
import requests

# Store memory
response = requests.post("http://localhost:8000/memories", json={
    "type": "solution",
    "title": "Python API Example",
    "content": "Using requests library with Memento",
    "tags": ["python", "api"],
    "importance": 0.7
})
memory_id = response.json()["id"]

# Search
search_response = requests.post("http://localhost:8000/search", json={
    "query": "python api",
    "limit": 10
})
results = search_response.json()["results"]
```

#### Using JavaScript fetch:
```javascript
// Store memory
const response = await fetch('http://localhost:8000/memories', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    type: 'solution',
    title: 'JavaScript API Example',
    content: 'Using fetch with Memento HTTP API',
    tags: ['javascript', 'api'],
    importance: 0.6
  })
});
const data = await response.json();
const memoryId = data.id;

// Search memories
const searchResponse = await fetch('http://localhost:8000/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'javascript',
    limit: 5
  })
});
const searchData = await searchResponse.json();
```

### Advanced Configuration

#### Environment Variables for HTTP Server:
```bash
# Database configuration
export MEMENTO_SQLITE_PATH="/data/memento.db"

# Server configuration
export MEMENTO_HTTP_HOST="0.0.0.0"
export MEMENTO_HTTP_PORT="8000"
export MEMENTO_HTTP_WORKERS="4"

# Security (optional)
export MEMENTO_API_KEY="your-api-key-here"
export MEMENTO_CORS_ORIGINS="https://example.com,http://localhost:3000"
```

#### Adding Authentication (Optional):
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("MEMENTO_API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )

@app.post("/memories")
async def create_memory(memory: MemoryCreate, _ = Depends(verify_api_key)):
    # ... existing code ...
```

## Node.js Integration

### Overview
The Node.js integration allows you to use Memento directly from JavaScript/TypeScript applications. There are two approaches:
1. **Child Process**: Direct MCP protocol communication (recommended)
2. **HTTP Client**: Use the REST API via HTTP

### Child Process Integration (Recommended)

#### Installation:
```bash
npm install child_process  # Built-in, no extra installation needed
```

#### MementoClient Class:
```javascript
// memento-client.js
const { spawn } = require('child_process');
const { Readable, Writable } = require('stream');

class MementoClient {
  constructor(options = {}) {
    this.options = {
      profile: options.profile || 'core',
      dbPath: options.dbPath || '~/.memento/context.db',
      ...options
    };
    
    this.server = null;
    this.requestId = 1;
  }

  start() {
    return new Promise((resolve, reject) => {
      this.server = spawn('memento', [
        '--profile', this.options.profile,
        '--log-level', 'ERROR'
      ]);
      
      this.server.stdout.on('data', (data) => {
        console.log(`Memento: ${data.toString().trim()}`);
      });
      
      this.server.stderr.on('data', (data) => {
        console.error(`Memento error: ${data.toString().trim()}`);
      });
      
      this.server.on('close', (code) => {
        console.log(`Memento exited with code ${code}`);
      });
      
      // Wait for server to be ready
      setTimeout(resolve, 2000);
    });
  }

  stop() {
    if (this.server) {
      this.server.kill();
    }
  }

  async sendRequest(method, params) {
    return new Promise((resolve, reject) => {
      const request = {
        jsonrpc: '2.0',
        id: this.requestId++,
        method,
        params
      };

      this.server.stdin.write(JSON.stringify(request) + '\n');
      
      const listener = (data) => {
        try {
          const response = JSON.parse(data.toString());
          if (response.id === request.id) {
            this.server.stdout.removeListener('data', listener);
            resolve(response.result);
          }
        } catch (error) {
          // Not JSON, continue listening
        }
      };
      
      this.server.stdout.on('data', listener);
      
      // Timeout after 10 seconds
      setTimeout(() => {
        this.server.stdout.removeListener('data', listener);
        reject(new Error('Request timeout'));
      }, 10000);
    });
  }

  async searchMemories(query, limit = 10) {
    return this.sendRequest('tools/call', {
      name: 'recall_mementos',
      arguments: {
        query,
        limit
      }
    });
  }

  async storeMemory(memoryData) {
    return this.sendRequest('tools/call', {
      name: 'store_memento',
      arguments: memoryData
    });
  }

  async getMemory(memoryId) {
    return this.sendRequest('tools/call', {
      name: 'get_memento',
      arguments: { memory_id: memoryId }
    });
  }

  async getStatistics() {
    return this.sendRequest('tools/call', {
      name: 'get_memento_statistics',
      arguments: {}
    });
  }
}

module.exports = MementoClient;
```

#### Usage Example:
```javascript
const MementoClient = require('./memento-client');

async function main() {
  const client = new MementoClient({ profile: 'extended' });
  
  try {
    await client.start();
    console.log('Memento client started');
    
    // Store a memory
    const memoryId = await client.storeMemory({
      type: 'solution',
      title: 'Node.js Integration Example',
      content: 'Example of integrating Memento with Node.js',
      tags: ['nodejs', 'integration', 'example'],
      importance: 0.6
    });
    
    console.log(`Stored memory with ID: ${memoryId}`);
    
    // Search memories
    const results = await client.searchMemories('Node.js integration', 5);
    console.log(`Found ${results.length} memories`);
    
    // Get statistics
    const stats = await client.getStatistics();
    console.log('Database statistics:', stats);
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    client.stop();
  }
}

if (require.main === module) {
  main();
}
```

#### TypeScript Support:
```typescript
// memento-client.d.ts
interface MementoOptions {
  profile?: 'core' | 'extended' | 'advanced';
  dbPath?: string;
}

interface MemoryData {
  type: string;
  title: string;
  content: string;
  tags?: string[];
  importance?: number;
}

declare class MementoClient {
  constructor(options?: MementoOptions);
  start(): Promise<void>;
  stop(): void;
  searchMemories(query: string, limit?: number): Promise<any[]>;
  storeMemory(memoryData: MemoryData): Promise<string>;
  getMemory(memoryId: string): Promise<any>;
  getStatistics(): Promise<any>;
}

export default MementoClient;
```

### HTTP Client Integration (Alternative)

```javascript
// Using the HTTP REST API from Node.js
const axios = require('axios');

class MementoHttpClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.client = axios.create({ baseURL });
  }

  async storeMemory(memoryData) {
    const response = await this.client.post('/memories', memoryData);
    return response.data.id;
  }

  async searchMemories(query, limit = 10) {
    const response = await this.client.post('/search', {
      query,
      limit
    });
    return response.data.results;
  }

  async getMemory(memoryId) {
    const response = await this.client.get(`/memories/${memoryId}`);
    return response.data;
  }

  async getStatistics() {
    const response = await this.client.get('/statistics');
    return response.data;
  }
}

// Usage
const client = new MementoHttpClient();
const memoryId = await client.storeMemory({
  type: 'solution',
  title: 'HTTP Client Example',
  content: 'Using axios with Memento HTTP API',
  tags: ['nodejs', 'http', 'axios']
});
```

## Docker Deployment

### Overview
Docker provides a consistent environment for running Memento in production, development, or testing scenarios. The official Docker image includes all dependencies and can be easily configured.

### Dockerfile
```dockerfile
# Dockerfile for MCP Memento Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY src/ ./src/
COPY run_mcp_memento.py .

# Create non-root user
RUN useradd -m -u 1000 memento && \
    chown -R memento:memento /app
USER memento

# Create data directory
RUN mkdir -p /app/data && chown memento:memento /app/data

# Run the memory server
# Note: MCP uses stdio transport, so stdin_open and tty are required in docker-compose
CMD ["python", "-m", "memento"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  memento:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: memento
    environment:
      - MEMENTO_SQLITE_PATH=/app/data/memento.db
      - MEMENTO_TOOL_PROFILE=extended
      - MEMENTO_LOG_LEVEL=INFO
    volumes:
      - memento_data:/app/data
      # Mount custom config (optional)
      - ./memento.yaml:/app/memento.yaml:ro
    ports:
      # For HTTP API (if using the HTTP wrapper)
      - "8000:8000"
    # Required for MCP stdio transport
    stdin_open: true
    tty: true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-m", "memento", "--health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  memento_data:
```

### Building and Running

#### Build the image:
```bash
docker build -t mcp-memento:latest .
```

#### Run with docker-compose:
```bash
docker-compose up -d
```

#### Run standalone container:
```bash
docker run -d \
  --name memento \
  -e MEMENTO_SQLITE_PATH=/data/memento.db \
  -e MEMENTO_TOOL_PROFILE=extended \
  -v ./memento-data:/data \
  -p 8000:8000 \
  mcp-memento:latest
```

### Docker Configuration Options

#### Environment Variables in Docker:
```bash
# Database configuration
MEMENTO_SQLITE_PATH=/data/memento.db

# Tool configuration
MEMENTO_TOOL_PROFILE=extended
MEMENTO_ENABLE_ADVANCED_TOOLS=false

# Logging
MEMENTO_LOG_LEVEL=INFO

# HTTP Server (if using HTTP wrapper)
MEMENTO_HTTP_HOST=0.0.0.0
MEMENTO_HTTP_PORT=8000
```

#### Volume Mounts:
```yaml
volumes:
  # Persistent database storage
  - ./data:/app/data
  
  # Custom configuration
  - ./config/memento.yaml:/app/memento.yaml:ro
  
  # Logs (optional)
  - ./logs:/app/logs
```

### Production Deployment

#### Kubernetes Deployment:
```yaml
# memento-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memento
spec:
  replicas: 1
  selector:
    matchLabels:
      app: memento
  template:
    metadata:
      labels:
        app: memento
    spec:
      containers:
      - name: memento
        image: mcp-memento:latest
        env:
        - name: MEMENTO_SQLITE_PATH
          value: "/data/memento.db"
        - name: MEMENTO_TOOL_PROFILE
          value: "extended"
        - name: MEMENTO_LOG_LEVEL
          value: "INFO"
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: memento-data
          mountPath: /data
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          exec:
            command: ["python", "-m", "memento", "--health"]
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command: ["python", "-m", "memento", "--health"]
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: memento-data
        persistentVolumeClaim:
          claimName: memento-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: memento-service
spec:
  selector:
    app: memento
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### Cloud Deployment Examples

#### AWS ECS (Fargate):
```yaml
# task-definition.json
{
  "family": "memento",
  "networkMode": "awsvpc",
  "executionRoleArn": "arn:aws:iam::account-id:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "memento",
      "image": "mcp-memento:latest",
      "essential": true,
      "environment": [
        {"name": "MEMENTO_SQLITE_PATH", "value": "/data/memento.db"},
        {"name": "MEMENTO_TOOL_PROFILE", "value": "extended"}
      ],
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/memento",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Google Cloud Run:
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/memento
gcloud run deploy memento \
  --image gcr.io/PROJECT_ID/memento \
  --platform managed \
  --region us-central1 \
  --set-env-vars="MEMENTO_SQLITE_PATH=/tmp/memento.db" \
  --memory 512Mi
```

## Python API Reference

For complete Python API documentation, see the [Python Integration Guide](./PYTHON.md). Key points:

### Direct Python Usage:
```python
import memento

# Create server instance
server = memento.Memento()

# Initialize (async)
await server.initialize()

# Use MCP tools directly
memory_id = await server.store_memory(
    type="solution",
    title="Python API Example",
    content="Direct Python integration",
    tags=["python", "api"],
    importance=0.8
)

# Search memories
results = await server.recall_memories(query="python api")
```

### Integration with Existing Applications:
```python
from memento import Memento

class MyApplication:
    def __init__(self):
        self.memento = Memento()
    
    async def start(self):
        await self.memento.initialize()
    
    async def store_solution(self, title, content):
        return await self.memento.store_memory(
            type="solution",
            title=title,
            content=content,
            tags=["myapp", "solution"]
        )
```

## Best Practices

### Security Considerations
1. **API Keys**: Always use API keys for production HTTP APIs
2. **CORS**: Configure CORS appropriately for web applications
3. **Input Validation**: Validate all inputs before passing to Memento
4. **Rate Limiting**: Implement rate limiting for public APIs
5. **Database Encryption**: Consider encrypting sensitive database contents

### Performance Optimization
1. **Connection Pooling**: Reuse connections for HTTP clients
2. **Caching**: Cache frequently accessed memories
3. **Batch Operations**: Use batch operations when storing multiple memories
4. **Database Maintenance**: Regular VACUUM and ANALYZE for SQLite
5. **Memory Limits**: Set appropriate memory limits for containers

### Monitoring and Logging
1. **Health Checks**: Implement comprehensive health checks
2. **Metrics**: Track API usage, memory counts, confidence scores
3. **Logging**: Structured logging with correlation IDs
4. **Alerting**: Set up alerts for low confidence memories
5. **Backup**: Regular database backups

### Backup Strategies
```bash
# Simple backup script
#!/bin/bash
BACKUP_DIR="/backups/memento"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/data/memento.db"

# Create backup
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/memento_$DATE.db'"

# Keep only last 7 days
find "$BACKUP_DIR" -name "memento_*.db" -mtime +7 -delete
```

## Troubleshooting

### Common Issues

#### HTTP API Won't Start:
```bash
# Check dependencies
pip list | grep fastapi

# Check port availability
netstat -tulpn | grep :8000

# Check logs
python memento-http.py 2>&1 | tail -20
```

#### Node.js Client Connection Issues:
```javascript
// Enable debug logging
const client = new MementoClient({ 
  profile: 'extended',
  debug: true  // Add debug option to client
});
```

#### Docker Container Exits Immediately:
```bash
# Check container logs
docker logs memento

# Run with interactive mode
docker run -it --rm mcp-memento:latest python -m memento --health
```

#### Performance Issues:
```sql
-- Check database size
SELECT name, page_count * page_size as size_bytes 
FROM pragma_page_count(), pragma_page_size();

-- Check index usage
ANALYZE;
SELECT * FROM sqlite_stat1;
```

### Debugging Tips
1. **Enable Debug Logging**:
   ```bash
   MEMENTO_LOG_LEVEL=DEBUG python -m memento
   ```

2. **Test Direct MCP Communication**:
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | python -m memento
   ```

3. **Check Database Integrity**:
   ```bash
   sqlite3 memento.db "PRAGMA integrity_check;"
   ```

4. **Monitor Memory Usage**:
   ```bash
   # Linux
   ps aux | grep memento
   
   # Docker
   docker stats memento
   ```

### Performance Tuning
1. **SQLite Configuration**:
   ```python
   # In your application
   import sqlite3
   conn = sqlite3.connect('memento.db')
   conn.execute('PRAGMA journal_mode = WAL;')
   conn.execute('PRAGMA synchronous = NORMAL;')
   conn.execute('PRAGMA cache_size = -2000;')  # 2MB cache
   ```

2. **Connection Pool Sizing**:
   ```python
   # HTTP server with connection pool
   from databases import Database
   database = Database('sqlite:///memento.db', min_size=1, max_size=10)
   ```

3. **Query Optimization**:
   ```sql
   -- Add missing indexes
   CREATE INDEX IF NOT EXISTS idx_memory_tags 
   ON nodes(json_each.value) 
   WHERE label = 'Memory' 
   AND json_each.key = 'tags';
   ```

## Conclusion

Memento provides flexible API integration options for every use case:

- **HTTP REST API**: Best for web applications and cross-language systems
- **Node.js SDK**: Ideal for JavaScript/TypeScript applications
- **Python API**: Perfect for Python scripts and services
- **Docker Deployment**: Recommended for production environments

All APIs share the same underlying memory storage and confidence system, ensuring consistent behavior across all integration points. Choose the API that best fits your application's architecture and requirements.

For more information, see:
- [Python Integration Guide](./PYTHON.md) - Detailed Python API documentation
- [IDE Integration Guide](./IDE.md) - IDE-specific configuration
- [Agent Integration Guide](./AGENT.md) - CLI agent integration
- [Tools Reference](../TOOLS.md) - Complete MCP tool documentation

Need help? Check the [troubleshooting guide](../TROUBLESHOOTING.md) or open an issue on GitHub.