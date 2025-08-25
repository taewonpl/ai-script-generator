# OpenAPI Type Auto-Generation System

This document explains the OpenAPI type auto-generation system that provides type-safe API clients with runtime validation using Zod schemas.

## 🏗️ System Overview

The OpenAPI system automatically generates:

- **TypeScript Types** - Static type definitions from OpenAPI specs
- **Zod Schemas** - Runtime validation schemas for API requests/responses
- **API Clients** - Pre-configured Axios clients with proper typing

## 📁 Directory Structure

```
src/shared/api/generated/
├── types/              # TypeScript type definitions
│   ├── core-types.ts      # Core Service types
│   ├── project-types.ts   # Project Service types
│   ├── generation-types.ts # Generation Service types
│   └── index.ts           # Type exports
├── schemas/            # Zod validation schemas
│   ├── core-schemas.ts    # Core Service schemas
│   ├── project-schemas.ts # Project Service schemas
│   ├── generation-schemas.ts # Generation Service schemas
│   └── index.ts           # Schema exports
├── clients/            # API client configurations
│   └── index.ts           # Pre-configured clients
└── .gitkeep           # Directory documentation
```

## 🚀 Quick Start

### 1. Generate All Types and Schemas

```bash
# Generate everything at once
npm run generate:all

# Or step by step
npm run generate:all-types    # TypeScript types only
npm run generate:all-schemas  # Zod schemas only
```

### 2. Start Development with Auto-generation

```bash
# Generate types and start dev server
npm run dev:with-types
```

### 3. Use Generated Types in Code

```typescript
// Import generated types
import type { Project, Episode } from '@shared/api/generated/types'

// Import validation schemas
import { ProjectSchema, EpisodeSchema } from '@shared/api/generated/schemas'

// Import pre-configured clients
import { apiClients } from '@shared/api/generated/clients'

// Use type-safe API calls
const project: Project = await apiClients.project.get('/projects/123')
const validatedData = ProjectSchema.parse(responseData)
```

## 🛠️ Available Scripts

### Individual Service Generation

```bash
# TypeScript Types
npm run generate:core-types        # Core Service types
npm run generate:project-types     # Project Service types
npm run generate:generation-types  # Generation Service types

# Zod Schemas
npm run generate:core-schemas      # Core Service schemas
npm run generate:project-schemas   # Project Service schemas
npm run generate:generation-schemas # Generation Service schemas
```

### Batch Generation

```bash
npm run generate:all-types    # All TypeScript types
npm run generate:all-schemas  # All Zod schemas
npm run generate:all         # Everything
```

### Development Workflow

```bash
npm run dev:with-types  # Generate types + start dev server
```

## 📋 Service Configuration

Each service requires a running backend with OpenAPI documentation:

| Service                | URL                     | OpenAPI Endpoint |
| ---------------------- | ----------------------- | ---------------- |
| **Core Service**       | `http://localhost:8000` | `/openapi.json`  |
| **Project Service**    | `http://localhost:8001` | `/openapi.json`  |
| **Generation Service** | `http://localhost:8002` | `/openapi.json`  |

## 🔧 Generated API Clients

The system provides pre-configured Axios clients with:

### Environment-Based Configuration

```typescript
// Development: Uses Vite proxy
const client = axios.create({
  baseURL: '/project-api', // → proxied to localhost:8001
})

// Production: Direct URLs
const client = axios.create({
  baseURL: 'https://project-api.yourdomain.com/api',
})
```

### Built-in Features

- ✅ **Request/Response Logging** (development only)
- ✅ **Authentication Interceptors** (Bearer token)
- ✅ **Error Handling** (401 → redirect to login)
- ✅ **Timeout Configuration** (service-specific)
- ✅ **Type Safety** (full TypeScript support)

### Usage Examples

```typescript
import { apiClients } from '@shared/api/client'

// Type-safe API calls
const projects = await apiClients.project.get('/projects')
const newProject = await apiClients.project.post('/projects', projectData)

// With generated types
import type { Project } from '@shared/api/generated/types'
const project: Project = response.data
```

## 🛡️ Runtime Validation with Zod

### Schema Generation

Zod schemas are automatically generated from OpenAPI specifications:

```typescript
// Auto-generated from OpenAPI
export const ProjectSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.enum(['drama', 'comedy', 'action']),
  status: z.enum(['active', 'completed', 'archived']),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
})

export type Project = z.infer<typeof ProjectSchema>
```

### Validation Helpers

```typescript
import { validateSchema, isValidSchema } from '@shared/api/generated/schemas'

// Validate API response
try {
  const project = validateSchema(ProjectSchema, apiResponse)
  // project is now type-safe and validated
} catch (error) {
  console.error('Invalid project data:', error.message)
}

// Check validity without throwing
if (isValidSchema(ProjectSchema, data)) {
  // data is valid
}
```

### Request/Response Validation

```typescript
// Validate request payload before sending
const createProjectData = {
  name: 'My Project',
  type: 'drama',
  description: 'A great story',
}

// This will throw if data is invalid
const validatedData = ProjectCreateSchema.parse(createProjectData)
const response = await apiClients.project.post('/projects', validatedData)

// Validate response data
const project = ProjectSchema.parse(response.data)
```

## 🔄 Automatic Regeneration

### During Development

The build system can regenerate types automatically:

```bash
# Watch for OpenAPI changes and regenerate
npm run dev:with-types
```

### CI/CD Integration

Add to your build pipeline:

```yaml
# GitHub Actions example
- name: Generate API Types
  run: |
    npm install
    npm run generate:all
    npm run build
```

### Pre-commit Hook

```bash
# .husky/pre-commit
npm run generate:all
git add src/shared/api/generated/
```

## 🚨 Troubleshooting

### Service Not Running

```bash
❌ Failed to generate Zod schemas for core: Error: connect ECONNREFUSED 127.0.0.1:8000
💡 Make sure the service is running and accessible at: http://localhost:8000/openapi.json
```

**Solution:** Start the backend service before generating types.

### Invalid OpenAPI Spec

```bash
❌ Failed to generate Zod schemas for project: Invalid OpenAPI specification
💡 The OpenAPI specification may be invalid or incomplete
```

**Solution:** Check the OpenAPI endpoint returns valid JSON schema.

### Import Errors After Generation

```typescript
❌ Cannot find module '@shared/api/generated/types'
```

**Solution:** Run `npm run generate:all` to create the generated files.

### Type Conflicts

```typescript
❌ Type 'Project' is not assignable to type 'Project'
```

**Solution:** You may be mixing manually-defined and generated types. Use only generated types.

## 🔧 Customization

### Adding New Services

1. **Add Environment Variables:**

   ```bash
   # .env
   VITE_NEW_SERVICE_URL=http://localhost:8003
   ```

2. **Update Environment Validation:**

   ```typescript
   // src/shared/config/env.ts
   VITE_NEW_SERVICE_URL: z.string().url('New Service URL is invalid'),
   ```

3. **Add Generation Scripts:**

   ```json
   {
     "scripts": {
       "generate:new-types": "openapi-typescript http://localhost:8003/openapi.json -o src/shared/api/generated/types/new-types.ts",
       "generate:new-schemas": "node scripts/generate-zod-schemas.js new http://localhost:8003/openapi.json"
     }
   }
   ```

4. **Update Vite Proxy:**
   ```typescript
   // vite.config.ts
   proxy: {
     '/new-api': {
       target: env.VITE_NEW_SERVICE_URL,
       changeOrigin: true,
       rewrite: path => path.replace(/^\/new-api/, '/api'),
     }
   }
   ```

### Custom Schema Validation

```typescript
// Extend generated schemas
import { ProjectSchema } from '@shared/api/generated/schemas'

const ExtendedProjectSchema = ProjectSchema.extend({
  customField: z.string().optional(),
}).refine(data => {
  // Custom validation logic
  return data.name.length > 0
}, 'Project name cannot be empty')
```

### Custom API Client Configuration

```typescript
// Custom client with different settings
import { projectApiClient } from '@shared/api/generated/clients'

const customProjectClient = projectApiClient.create({
  timeout: 60000, // Longer timeout
  headers: {
    'Custom-Header': 'value',
  },
})
```

## 📊 Performance Considerations

### Generation Time

- **TypeScript Types**: ~1-2 seconds per service
- **Zod Schemas**: ~2-3 seconds per service
- **Total Time**: ~10-15 seconds for all services

### Bundle Size Impact

- **Types**: No runtime impact (compile-time only)
- **Schemas**: ~10-50KB per service (runtime validation)
- **Clients**: ~2-5KB per service

### Caching

- Generated files are cached until OpenAPI specs change
- Use `npm run generate:all` to force regeneration
- Consider adding `.generated` to `.gitignore` for large teams

## 🧪 Testing with Generated Types

### Unit Tests

```typescript
import { describe, it, expect } from 'vitest'
import { ProjectSchema } from '@shared/api/generated/schemas'

describe('Project Schema', () => {
  it('validates correct project data', () => {
    const validProject = {
      id: '123',
      name: 'Test Project',
      type: 'drama',
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    expect(() => ProjectSchema.parse(validProject)).not.toThrow()
  })

  it('rejects invalid project data', () => {
    const invalidProject = {
      id: 123, // Should be string
      name: '',
      type: 'invalid-type',
    }

    expect(() => ProjectSchema.parse(invalidProject)).toThrow()
  })
})
```

### API Testing

```typescript
import { apiClients } from '@shared/api/client'
import { ProjectSchema } from '@shared/api/generated/schemas'

describe('Project API', () => {
  it('returns valid project data', async () => {
    const response = await apiClients.project.get('/projects/123')

    // This will throw if response doesn't match schema
    const project = ProjectSchema.parse(response.data)

    expect(project.id).toBe('123')
    expect(project.name).toBeTruthy()
  })
})
```

## 🔒 Security Best Practices

### Type Safety

- ✅ **Never bypass type checking** - Always use generated types
- ✅ **Validate all external data** - Use Zod schemas for API responses
- ✅ **Handle validation errors** - Don't ignore schema validation failures

### API Security

```typescript
// ❌ Don't expose sensitive data in types
type User = {
  id: string
  name: string
  password: string // This will be in the bundle!
}

// ✅ Keep sensitive data server-side only
type User = {
  id: string
  name: string
  email: string
}
```

### Environment Variables

- ✅ **Validate all URLs** - Use Zod URL validation
- ✅ **Use HTTPS in production** - Enforce in environment validation
- ❌ **Never expose secrets** - API keys should not be in VITE\_ variables

## 📚 Related Documentation

- [Environment Configuration](./ENVIRONMENT.md)
- [API Client Usage](./README.md#api-clients)
- [Zod Documentation](https://zod.dev/)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.0.3)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)

---

**The OpenAPI system provides end-to-end type safety from backend to frontend! 🛡️**
