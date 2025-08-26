import { useState, useEffect } from 'react'
import type { SyntheticEvent } from 'react'
import { Controller } from 'react-hook-form'
import type { FieldValues } from 'react-hook-form'
import type { AutocompleteProps, FilterOptionsState } from '@mui/material'
import { Autocomplete, TextField, Chip, CircularProgress } from '@mui/material'
import type { BaseFormProps } from './types'

export interface AutocompleteOption {
  value: string | number
  label: string
  group?: string
  disabled?: boolean
  description?: string
}

export interface FormAutocompleteProps<T extends FieldValues>
  extends BaseFormProps<T>,
    Omit<
      AutocompleteProps<AutocompleteOption, boolean, boolean, boolean>,
      'name' | 'value' | 'onChange' | 'renderInput' | 'options'
    > {
  options: AutocompleteOption[]
  placeholder?: string
  multiple?: boolean
  freeSolo?: boolean
  loading?: boolean
  loadingText?: string
  noOptionsText?: string
  groupBy?: (option: AutocompleteOption) => string
  getOptionLabel?: (option: AutocompleteOption | string) => string
  isOptionEqualToValue?: (
    option: AutocompleteOption,
    value: AutocompleteOption,
  ) => boolean
  filterOptions?: (
    options: AutocompleteOption[],
    state: FilterOptionsState<AutocompleteOption>,
  ) => AutocompleteOption[]
  onInputChange?: (event: SyntheticEvent, value: string, reason: string) => void
  asyncSearch?: (inputValue: string) => Promise<AutocompleteOption[]>
}

/**
 * Material-UI Autocomplete integrated with React Hook Form
 *
 * Features:
 * - Single and multiple selection
 * - Free solo input
 * - Async search support
 * - Option grouping
 * - Loading states
 * - Custom filtering
 */
export function FormAutocomplete<T extends FieldValues>({
  control,
  name,
  label,
  placeholder,
  helperText,
  disabled = false,
  required = false,
  fullWidth = true,
  options: initialOptions,
  multiple = false,
  freeSolo = false,
  loading = false,
  loadingText = '로딩 중...',
  noOptionsText = '옵션이 없습니다',
  groupBy,
  getOptionLabel,
  isOptionEqualToValue,
  filterOptions,
  onInputChange,
  asyncSearch,
  size = 'medium',
  ...autocompleteProps
}: FormAutocompleteProps<T>) {
  // Using control prop instead of form context for better type safety
  const [options, setOptions] = useState<AutocompleteOption[]>(initialOptions)
  const [asyncLoading, setAsyncLoading] = useState(false)
  const [inputValue, setInputValue] = useState('')

  // Default option label getter
  const defaultGetOptionLabel = (option: AutocompleteOption | string) => {
    if (typeof option === 'string') return option
    return option.label
  }

  // Default option equality checker
  const defaultIsOptionEqualToValue = (
    option: AutocompleteOption,
    value: AutocompleteOption,
  ) => {
    return option.value === value.value
  }

  // Handle async search
  useEffect(() => {
    if (!asyncSearch || !inputValue) return

    const searchTimeout = setTimeout(async () => {
      setAsyncLoading(true)
      try {
        const searchResults = await asyncSearch(inputValue)
        setOptions(searchResults)
      } catch (error) {
        console.error('Async search error:', error)
      } finally {
        setAsyncLoading(false)
      }
    }, 300) // Debounce search

    return () => clearTimeout(searchTimeout)
  }, [inputValue, asyncSearch])

  // Handle input change
  const handleInputChange = (
    event: SyntheticEvent,
    value: string,
    reason: string,
  ) => {
    setInputValue(value)
    onInputChange?.(event, value, reason)
  }

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => {
        const hasError = !!fieldState.error
        const errorMessage = fieldState.error?.message
        const displayHelperText = errorMessage || helperText

        // Handle value conversion for form
        const fieldValue = field.value ?? (multiple ? [] : null)

        const handleChange = (
          _event: SyntheticEvent,
          value: any,
          _reason: any,
        ) => {
          if (multiple) {
            field.onChange(value || [])
          } else {
            field.onChange(value)
          }
        }

        return (
          <Autocomplete
            {...autocompleteProps}
            options={options}
            value={fieldValue}
            multiple={multiple}
            freeSolo={freeSolo}
            loading={loading || asyncLoading}
            loadingText={loadingText}
            noOptionsText={noOptionsText}
            groupBy={groupBy}
            getOptionLabel={getOptionLabel || defaultGetOptionLabel}
            isOptionEqualToValue={
              isOptionEqualToValue || defaultIsOptionEqualToValue
            }
            filterOptions={filterOptions}
            disabled={disabled}
            size={size}
            fullWidth={fullWidth}
            onChange={handleChange}
            onInputChange={handleInputChange}
            renderInput={params => (
              <TextField
                {...params}
                label={label}
                placeholder={placeholder}
                error={hasError}
                helperText={displayHelperText}
                required={required}
                variant="outlined"
                margin="normal"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {(loading || asyncLoading) && (
                        <CircularProgress color="inherit" size={20} />
                      )}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => (
                <Chip
                  label={typeof option === 'string' ? option : option.label}
                  size="small"
                  {...getTagProps({ index })}
                />
              ))
            }
            renderOption={(props, option) => (
              <li {...props}>
                <div>
                  <div>{option.label}</div>
                  {option.description && (
                    <div style={{ fontSize: '0.875rem', color: '#666' }}>
                      {option.description}
                    </div>
                  )}
                </div>
              </li>
            )}
          />
        )
      }}
    />
  )
}

/**
 * Multi-select autocomplete variant
 */
export function FormMultiAutocomplete<T extends FieldValues>(
  props: Omit<FormAutocompleteProps<T>, 'multiple'>,
) {
  return <FormAutocomplete {...props} multiple />
}

/**
 * Free solo autocomplete for custom input
 */
export function FormFreeSoloAutocomplete<T extends FieldValues>(
  props: Omit<FormAutocompleteProps<T>, 'freeSolo'>,
) {
  return <FormAutocomplete {...props} freeSolo />
}
