#!/usr/bin/env node

const fs = require('fs')
const path = require('path')
const { generateZodClientFromOpenAPI } = require('openapi-zod-client')

/**
 * Generate Zod schemas from OpenAPI specifications
 * Usage: node scripts/generate-zod-schemas.js <service-name> <openapi-url>
 */

const [, , serviceName, openApiUrl] = process.argv

if (!serviceName || !openApiUrl) {
  console.error(
    '❌ Usage: node scripts/generate-zod-schemas.js <service-name> <openapi-url>',
  )
  console.error(
    '   Example: node scripts/generate-zod-schemas.js core http://localhost:8000/openapi.json',
  )
  process.exit(1)
}

const OUTPUT_DIR = path.join(
  __dirname,
  '..',
  'src',
  'shared',
  'api',
  'generated',
  'schemas',
)
const outputFile = path.join(OUTPUT_DIR, `${serviceName}-schemas.ts`)

async function generateSchemas() {
  try {
    console.log(`🔄 Generating Zod schemas for ${serviceName} service...`)
    console.log(`📡 Fetching OpenAPI spec from: ${openApiUrl}`)

    // Ensure output directory exists
    if (!fs.existsSync(OUTPUT_DIR)) {
      fs.mkdirSync(OUTPUT_DIR, { recursive: true })
    }

    // Generate Zod schemas
    await generateZodClientFromOpenAPI({
      openApiDoc: openApiUrl,
      distPath: outputFile,
      options: {
        // Include all schemas from the OpenAPI spec
        withAlias: true,
        // Generate both request and response schemas
        baseUrl: '',
        // Export individual schemas for reuse
        exportAllTypes: true,
        // Use consistent naming
        groupStrategy: 'none',
        // Enable strict mode for better validation
        strict: {
          query: true,
          header: true,
          body: true,
        },
        // Custom template options
        templatePath: undefined,
        // Additional validation options
        additionalProperties: false,
        // Include descriptions from OpenAPI
        withDescription: true,
      },
    })

    // Add custom header and exports to the generated file
    const generatedContent = fs.readFileSync(outputFile, 'utf8')
    const customHeader = `/**
 * Auto-generated Zod schemas for ${serviceName.toUpperCase()} Service
 *
 * Generated from: ${openApiUrl}
 * Generated at: ${new Date().toISOString()}
 *
 * ⚠️ DO NOT EDIT MANUALLY - This file is auto-generated
 * To regenerate: npm run generate:${serviceName}-schemas
 */

`

    // Write the final file with custom header
    fs.writeFileSync(outputFile, customHeader + generatedContent)

    console.log(`✅ Successfully generated Zod schemas: ${outputFile}`)

    // Create index file for easier imports
    await createSchemaIndex()
  } catch (error) {
    console.error(
      `❌ Failed to generate Zod schemas for ${serviceName}:`,
      error.message,
    )

    // Provide helpful error messages
    if (error.code === 'ECONNREFUSED') {
      console.error(
        '💡 Make sure the service is running and accessible at:',
        openApiUrl,
      )
    } else if (error.message.includes('404')) {
      console.error(
        '💡 OpenAPI endpoint not found. Check if the URL is correct:',
        openApiUrl,
      )
    } else if (error.message.includes('Invalid OpenAPI')) {
      console.error('💡 The OpenAPI specification may be invalid or incomplete')
    }

    process.exit(1)
  }
}

async function createSchemaIndex() {
  const indexPath = path.join(OUTPUT_DIR, 'index.ts')
  const schemaFiles = fs
    .readdirSync(OUTPUT_DIR)
    .filter(file => file.endsWith('-schemas.ts') && file !== 'index.ts')
    .map(file => file.replace('-schemas.ts', ''))

  if (schemaFiles.length === 0) {
    return
  }

  const indexContent = `/**
 * Auto-generated schema exports
 *
 * This file exports all generated Zod schemas for easy importing.
 *
 * ⚠️ DO NOT EDIT MANUALLY - This file is auto-generated
 */

${schemaFiles
  .map(
    service =>
      `// ${service.toUpperCase()} Service Schemas\nexport * from './${service}-schemas'`,
  )
  .join('\n\n')}

// Re-export commonly used Zod utilities
export { z } from 'zod'

// Schema validation helpers
export const validateSchema = <T>(schema: any, data: unknown): T => {
  const result = schema.safeParse(data)
  if (!result.success) {
    throw new Error(\`Schema validation failed: \${result.error.message}\`)
  }
  return result.data
}

export const isValidSchema = (schema: any, data: unknown): boolean => {
  return schema.safeParse(data).success
}
`

  fs.writeFileSync(indexPath, indexContent)
  console.log(`📝 Created schema index file: ${indexPath}`)
}

// Run the generation
generateSchemas().catch(error => {
  console.error('💥 Unexpected error:', error)
  process.exit(1)
})
