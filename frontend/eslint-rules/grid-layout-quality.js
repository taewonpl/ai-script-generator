/**
 * Custom ESLint rules for Grid layout quality assurance
 */

const gridLayoutQualityRules = {
  'no-grid-gap-conflict': {
    meta: {
      type: 'problem',
      docs: {
        description: 'Disallow conflicting spacing patterns in Grid layouts',
        category: 'Best Practices',
        recommended: true,
      },
      fixable: 'code',
      hasSuggestions: true,
      schema: [],
      messages: {
        gapConflict:
          'Avoid using CSS gap with Grid container spacing prop. Use spacing={{2}} instead of sx={{gap: 2}} for consistent behavior.',
        spacingAndGap:
          'Do not use both spacing prop and CSS gap simultaneously. Choose either spacing={{2}} OR sx={{gap: 2}}.',
        preferSpacing:
          'Use spacing prop instead of CSS gap for Grid containers to ensure proper negative margin handling.',
      },
    },
    create(context) {
      return {
        JSXElement(node) {
          const elementName = node.openingElement.name.name

          // Only check Grid components
          if (elementName !== 'Grid' && elementName !== 'Grid2') return

          const attributes = node.openingElement.attributes
          let hasSpacing = false
          let hasGapInSx = false
          let spacingAttr = null
          let sxAttr = null

          // Check all attributes
          attributes.forEach(attr => {
            if (attr.name && attr.name.name === 'spacing') {
              hasSpacing = true
              spacingAttr = attr
            }

            if (attr.name && attr.name.name === 'sx' && attr.value) {
              sxAttr = attr
              // Check if sx contains gap property
              if (attr.value.expression && attr.value.expression.properties) {
                attr.value.expression.properties.forEach(prop => {
                  if (prop.key && prop.key.name === 'gap') {
                    hasGapInSx = true
                  }
                })
              }
            }
          })

          // Report conflicts
          if (hasSpacing && hasGapInSx) {
            context.report({
              node,
              messageId: 'spacingAndGap',
              suggest: [
                {
                  desc: 'Remove CSS gap and use spacing prop only',
                  fix(fixer) {
                    // Remove gap from sx prop
                    if (sxAttr && sxAttr.value.expression.properties) {
                      const gapProp = sxAttr.value.expression.properties.find(
                        p => p.key.name === 'gap',
                      )
                      if (gapProp) {
                        return fixer.remove(gapProp)
                      }
                    }
                  },
                },
              ],
            })
          } else if (hasGapInSx && elementName === 'Grid') {
            context.report({
              node,
              messageId: 'preferSpacing',
            })
          }
        },
      }
    },
  },

  'grid2-migration-warning': {
    meta: {
      type: 'suggestion',
      docs: {
        description: 'Suggest migrating from Grid to Grid2',
        category: 'Best Practices',
        recommended: false,
      },
      schema: [],
      messages: {
        migrateToGrid2:
          'Consider migrating to Grid2 for better performance and modern layout features. Grid2 provides the same API with improved calculations.',
        useGrid2Import:
          'Import Grid2 as: import { Unstable_Grid2 as Grid2 } from "@mui/material"',
      },
    },
    create(context) {
      return {
        ImportDeclaration(node) {
          if (node.source.value === '@mui/material') {
            node.specifiers.forEach(spec => {
              if (spec.imported && spec.imported.name === 'Grid') {
                context.report({
                  node: spec,
                  messageId: 'useGrid2Import',
                })
              }
            })
          }
        },

        JSXElement(node) {
          const elementName = node.openingElement.name.name

          if (elementName === 'Grid') {
            const hasContainer = node.openingElement.attributes.some(
              attr => attr.name && attr.name.name === 'container',
            )

            if (hasContainer) {
              context.report({
                node,
                messageId: 'migrateToGrid2',
              })
            }
          }
        },
      }
    },
  },

  'grid-layout-validation': {
    meta: {
      type: 'problem',
      docs: {
        description: 'Validate Grid layout structure and usage patterns',
        category: 'Possible Errors',
        recommended: true,
      },
      schema: [],
      messages: {
        missingContainer:
          'Grid items should be wrapped in a Grid container. Add container prop to parent Grid.',
        itemWithoutContainer: 'Grid item found without Grid container parent.',
        invalidSpacing:
          'Grid spacing should be a number or responsive object, not string.',
        oversizedGrid:
          'Grid breakpoint values should not exceed 12. Found: {{value}}',
        unnecessaryItem:
          'Grid item prop is not needed when using only layout props (xs, sm, md, lg, xl).',
      },
    },
    create(context) {
      return {
        JSXElement(node) {
          const elementName = node.openingElement.name.name

          if (elementName !== 'Grid' && elementName !== 'Grid2') return

          const attributes = node.openingElement.attributes
          let hasContainer = false
          let hasItem = false
          let hasBreakpoints = false
          let spacingValue = null

          // Analyze attributes
          attributes.forEach(attr => {
            if (!attr.name) return

            const attrName = attr.name.name

            if (attrName === 'container') {
              hasContainer = true
            } else if (attrName === 'item') {
              hasItem = true
            } else if (['xs', 'sm', 'md', 'lg', 'xl'].includes(attrName)) {
              hasBreakpoints = true

              // Check for oversized grid values
              if (attr.value && attr.value.value) {
                const value = parseInt(attr.value.value)
                if (value > 12) {
                  context.report({
                    node: attr,
                    messageId: 'oversizedGrid',
                    data: { value: value },
                  })
                }
              }
            } else if (attrName === 'spacing') {
              spacingValue = attr.value
            }
          })

          // Validation logic
          if (hasBreakpoints && !hasItem && !hasContainer) {
            context.report({
              node,
              messageId: 'unnecessaryItem',
            })
          }

          if (
            spacingValue &&
            spacingValue.type === 'Literal' &&
            typeof spacingValue.value === 'string'
          ) {
            context.report({
              node: spacingValue,
              messageId: 'invalidSpacing',
            })
          }

          // Check for proper container/item relationship
          if (hasItem && !hasContainer) {
            // Look for parent Grid container
            let parent = node.parent
            let foundContainer = false

            while (parent && parent.type === 'JSXElement') {
              const parentName = parent.openingElement.name.name
              if (parentName === 'Grid' || parentName === 'Grid2') {
                const parentAttributes = parent.openingElement.attributes
                foundContainer = parentAttributes.some(
                  attr => attr.name && attr.name.name === 'container',
                )
                if (foundContainer) break
              }
              parent = parent.parent
            }

            if (!foundContainer) {
              context.report({
                node,
                messageId: 'itemWithoutContainer',
              })
            }
          }
        },
      }
    },
  },
}

export default { rules: gridLayoutQualityRules }
