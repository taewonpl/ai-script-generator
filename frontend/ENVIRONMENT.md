# Environment Configuration Guide

This guide explains the environment variable system with runtime validation using Zod.

## 🔧 Environment Variables

### Required Variables

| Variable                      | Description                     | Example                 | Validation                             |
| ----------------------------- | ------------------------------- | ----------------------- | -------------------------------------- |
| `VITE_CORE_SERVICE_URL`       | Core Service API endpoint       | `http://localhost:8000` | Must be valid URL                      |
| `VITE_PROJECT_SERVICE_URL`    | Project Service API endpoint    | `http://localhost:8001` | Must be valid URL                      |
| `VITE_GENERATION_SERVICE_URL` | Generation Service API endpoint | `http://localhost:8002` | Must be valid URL                      |
| `VITE_ENV`                    | Application environment         | `development`           | Must be: development, production, test |

### Optional Variables

| Variable               | Description                 | Example                     | Default        |
| ---------------------- | --------------------------- | --------------------------- | -------------- |
| `VITE_SENTRY_DSN`      | Sentry error tracking DSN   | `https://...@sentry.io/...` | Not configured |
| `VITE_APP_VERSION`     | Application version         | `1.0.0`                     | `1.0.0`        |
| `VITE_ENABLE_DEVTOOLS` | Enable React Query Devtools | `true`                      | `true`         |
| `VITE_ENABLE_MSW`      | Enable Mock Service Worker  | `true`                      | `true`         |

## 📁 Configuration Files

### Environment Files

- `.env` - Development environment variables
- `.env.example` - Template with all required variables
- `.env.production` - Production environment template (create manually)

### Configuration Code

- `src/shared/config/env.ts` - Runtime validation with Zod
- `src/vite-env.d.ts` - TypeScript type definitions

## 🚀 Quick Setup

1. **Copy the example file:**

   ```bash
   cp .env.example .env
   ```

2. **Update the URLs for your environment:**

   ```bash
   # Development (default)
   VITE_CORE_SERVICE_URL=http://localhost:8000
   VITE_PROJECT_SERVICE_URL=http://localhost:8001
   VITE_GENERATION_SERVICE_URL=http://localhost:8002

   # Production (example)
   VITE_CORE_SERVICE_URL=https://api.yourdomain.com
   VITE_PROJECT_SERVICE_URL=https://projects.yourdomain.com
   VITE_GENERATION_SERVICE_URL=https://generation.yourdomain.com
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

## 🔍 Runtime Validation

The environment validation happens at application startup:

### Success Example

```bash
✅ Environment variables validated successfully: {
  CORE_SERVICE_URL: 'http://localhost:8000',
  PROJECT_SERVICE_URL: 'http://localhost:8001',
  GENERATION_SERVICE_URL: 'http://localhost:8002',
  ENV: 'development',
  VERSION: '1.0.0',
  DEVTOOLS: true,
  MSW: true,
  SENTRY: '❌ Not configured'
}
```

### Error Example

```bash
❌ Environment validation failed:
  - VITE_CORE_SERVICE_URL: Core Service URL이 올바르지 않습니다
  - VITE_ENV: Invalid enum value. Expected 'development' | 'production' | 'test', received 'invalid'
```

## 🏗️ Architecture

### Environment Validation Flow

```
main.tsx (imports env first)
    ↓
src/shared/config/env.ts
    ↓
Zod validation schema
    ↓
✅ Success: Frozen env object
❌ Error: Throws with details
```

### API Client Integration

```typescript
// Development: Uses proxy
const projectApi = axios.create({
  baseURL: '/project-api/v1', // → http://localhost:8001/api/v1
})

// Production: Direct URLs
const projectApi = axios.create({
  baseURL: 'https://projects.yourdomain.com/api/v1',
})
```

## 🔧 Development vs Production

### Development Mode

- ✅ Validation logs to console
- ✅ Uses Vite proxy for API calls
- ✅ React Query Devtools enabled
- ✅ MSW (Mock Service Worker) enabled

### Production Mode

- ✅ Silent validation (errors still throw)
- ✅ Direct API URLs
- ❌ No devtools
- ❌ No MSW
- ✅ Sentry error tracking (if configured)

## 🛠️ Customization

### Adding New Environment Variables

1. **Update the Zod schema:**

   ```typescript
   // src/shared/config/env.ts
   const EnvSchema = z.object({
     // ... existing variables
     VITE_NEW_FEATURE_URL: z
       .string()
       .url('New feature URL is invalid')
       .describe('New feature service URL'),
   })
   ```

2. **Update TypeScript types:**

   ```typescript
   // src/vite-env.d.ts
   interface ImportMetaEnv {
     // ... existing variables
     readonly VITE_NEW_FEATURE_URL: string
   }
   ```

3. **Update .env.example:**
   ```bash
   # Add to .env.example
   VITE_NEW_FEATURE_URL=http://localhost:8003
   ```

### Custom Validation Rules

```typescript
// Example: Port validation
VITE_API_PORT: z.string()
  .regex(/^\d+$/, 'Port must be a number')
  .transform(Number)
  .refine(port => port > 0 && port < 65536, 'Port must be between 1-65535')

// Example: Environment-specific URLs
VITE_API_URL: z.string()
  .url()
  .refine(url => {
    if (process.env.NODE_ENV === 'production') {
      return url.startsWith('https://')
    }
    return true
  }, 'Production URLs must use HTTPS')
```

## 🧪 Testing Environment Validation

### Manual Testing

```bash
# Test with missing variable
unset VITE_CORE_SERVICE_URL
npm run dev  # Should fail with validation error

# Test with invalid URL
export VITE_CORE_SERVICE_URL="not-a-url"
npm run dev  # Should fail with URL validation error
```

### Automated Testing

```bash
# Run the validation test script
node test-env-validation.js
```

## 🚨 Common Issues

### Issue: "Environment validation failed"

**Cause:** Missing or invalid environment variables  
**Solution:** Check `.env` file and ensure all required variables are set with valid values

### Issue: "URL is not valid"

**Cause:** Environment variable is not a properly formatted URL  
**Solution:** Ensure URLs include protocol (`http://` or `https://`)

### Issue: "Invalid enum value"

**Cause:** `VITE_ENV` is not one of the allowed values  
**Solution:** Set to `development`, `production`, or `test`

### Issue: API calls failing in production

**Cause:** Environment URLs point to localhost  
**Solution:** Update environment variables to production URLs

## 🔒 Security Best Practices

### Environment Variable Naming

- ✅ Use `VITE_` prefix for client-side variables
- ❌ Never expose secrets (API keys, tokens) to client
- ✅ Use separate variables for different environments

### Production Setup

- ✅ Use HTTPS URLs in production
- ✅ Configure Sentry for error tracking
- ✅ Disable development features
- ✅ Use environment-specific .env files

### Secret Management

```bash
# ❌ Don't put secrets in client-side environment variables
VITE_API_SECRET=secret-key  # This will be exposed in the bundle!

# ✅ Use public configuration only
VITE_API_URL=https://api.example.com  # This is safe to expose
```

## 📚 Related Documentation

- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)
- [Zod Validation Library](https://zod.dev/)
- [TypeScript Environment Setup](./README.md#configuration)

---

**Environment validation ensures your application starts with valid configuration! 🛡️**
