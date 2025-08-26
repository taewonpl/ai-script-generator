import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { Controller } from 'react-hook-form'
import type { FieldValues } from 'react-hook-form'
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  Chip,
  Box,
} from '@mui/material'
import type { SelectProps } from '@mui/material'
import type { BaseFormProps } from './types'

export interface SelectOption {
  value: string | number
  label: string
  disabled?: boolean
  group?: string
}

export interface FormSelectProps<T extends FieldValues>
  extends BaseFormProps<T>,
    Omit<
      SelectProps,
      'name' | 'control' | 'value' | 'onChange' | 'label' | 'renderValue'
    > {
  options: SelectOption[]
  placeholder?: string
  multiple?: boolean
  renderValue?: (selected: string | string[]) => ReactNode
  emptyOption?: boolean
  emptyOptionLabel?: string
}

/**
 * Material-UI Select integrated with React Hook Form
 *
 * Features:
 * - Single and multiple selection
 * - Option groups
 * - Custom render for selected values
 * - Empty option support
 * - Error state handling
 */
export function FormSelect<T extends FieldValues>({
  control,
  name,
  label,
  placeholder: _placeholder,
  helperText,
  disabled = false,
  required = false,
  fullWidth = true,
  options,
  multiple = false,
  renderValue,
  emptyOption = false,
  emptyOptionLabel = '선택하세요',
  variant = 'outlined',
  size = 'medium',
  margin = 'none',
  ...selectProps
}: FormSelectProps<T>) {
  // Using control prop instead of form context for better type safety
  const labelId = `${String(name)}-label`

  // Group options by group property
  const groupedOptions = useMemo(() => {
    const groups: Record<string, SelectOption[]> = {}
    const ungrouped: SelectOption[] = []

    options.forEach(option => {
      if (option.group) {
        if (!groups[option.group]) {
          groups[option.group] = []
        }
        groups[option.group].push(option)
      } else {
        ungrouped.push(option)
      }
    })

    return { groups, ungrouped }
  }, [options])

  // Default render for multiple selection
  const defaultMultipleRender = (selected: string[]) => (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
      {selected.map(value => {
        const option = options.find(opt => opt.value === value)
        return <Chip key={value} label={option?.label || value} size="small" />
      })}
    </Box>
  )

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => {
        const hasError = !!fieldState.error
        const errorMessage = fieldState.error?.message
        const displayHelperText = errorMessage || helperText
        const fieldValue = field.value ?? (multiple ? [] : '')

        return (
          <FormControl
            fullWidth={fullWidth}
            error={hasError}
            disabled={disabled}
            variant={variant}
            size={size}
            margin={margin}
          >
            {label && (
              <InputLabel id={labelId} required={required}>
                {label}
              </InputLabel>
            )}

            <Select
              {...field}
              {...selectProps}
              labelId={labelId}
              value={fieldValue}
              label={label}
              multiple={multiple}
              renderValue={
                multiple
                  ? (renderValue as any) || defaultMultipleRender
                  : renderValue
              }
              onChange={event => {
                field.onChange(event.target.value)
              }}
            >
              {/* Empty option */}
              {emptyOption && !multiple && (
                <MenuItem value="">
                  <em>{emptyOptionLabel}</em>
                </MenuItem>
              )}

              {/* Ungrouped options */}
              {groupedOptions.ungrouped.map(option => (
                <MenuItem
                  key={option.value}
                  value={option.value}
                  {...(option.disabled && { disabled: option.disabled })}
                >
                  {option.label}
                </MenuItem>
              ))}

              {/* Grouped options */}
              {Object.entries(groupedOptions.groups).map(
                ([groupName, groupOptions]) => [
                  <MenuItem key={`group-${groupName}`} disabled={true}>
                    <strong>{groupName}</strong>
                  </MenuItem>,
                  ...groupOptions.map(option => (
                    <MenuItem
                      key={option.value}
                      value={option.value}
                      {...(option.disabled && { disabled: option.disabled })}
                      sx={{ pl: 4 }}
                    >
                      {option.label}
                    </MenuItem>
                  )),
                ],
              )}
            </Select>

            {displayHelperText && (
              <FormHelperText>{displayHelperText}</FormHelperText>
            )}
          </FormControl>
        )
      }}
    />
  )
}

/**
 * Multi-select variant
 */
export function FormMultiSelect<T extends FieldValues>(
  props: Omit<FormSelectProps<T>, 'multiple'>,
) {
  return <FormSelect {...props} multiple />
}
