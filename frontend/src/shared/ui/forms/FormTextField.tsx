import { useState } from 'react'
import type { ReactNode } from 'react'
import { Controller } from 'react-hook-form'
import type { FieldValues } from 'react-hook-form'
import { TextField } from '@mui/material'
import type { TextFieldProps } from '@mui/material'
import type { BaseFormProps } from './types'

export interface FormTextFieldProps<T extends FieldValues>
  extends BaseFormProps<T>,
    Omit<
      TextFieldProps,
      | 'name'
      | 'control'
      | 'defaultValue'
      | 'value'
      | 'onChange'
      | 'helperText'
      | 'label'
    > {
  placeholder?: string
  multiline?: boolean
  rows?: number
  maxRows?: number
  // HTML input types with modern support
  type?:
    | 'text'
    | 'email'
    | 'password'
    | 'url'
    | 'tel'
    | 'search'
    | 'number'
    | 'date'
    | 'datetime-local'
    | 'time'
    | 'checkbox'
  // Enhanced mobile input experience
  inputMode?:
    | 'text'
    | 'numeric'
    | 'decimal'
    | 'tel'
    | 'search'
    | 'email'
    | 'url'
    | 'none'
  pattern?: string
  autoComplete?: string
  startAdornment?: ReactNode
  endAdornment?: ReactNode
  // Input validation props
  min?: number | string
  max?: number | string
  step?: number | string
}

/**
 * Material-UI TextField integrated with React Hook Form
 *
 * Features:
 * - Full RHF integration with validation
 * - Error state handling
 * - Auto-focus support
 * - Input adornments
 * - Multi-line support
 * - Custom validation messages
 */
export function FormTextField<T extends FieldValues>({
  control,
  name,
  label,
  placeholder,
  helperText,
  disabled = false,
  required = false,
  fullWidth = true,
  multiline = false,
  rows,
  maxRows,
  type = 'text',
  inputMode,
  pattern,
  min,
  max,
  step,
  autoComplete,
  startAdornment,
  endAdornment,
  variant = 'outlined',
  size = 'medium',
  margin = 'normal',
  ...textFieldProps
}: FormTextFieldProps<T>) {
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => {
        const hasError = !!fieldState.error
        const errorMessage = fieldState.error?.message
        const displayHelperText = errorMessage || helperText

        // Enhanced input props for better UX
        const inputProps = {
          inputMode,
          pattern,
          min,
          max,
          step,
          ...textFieldProps.inputProps,
        }

        return (
          <TextField
            {...field}
            {...textFieldProps}
            label={label}
            placeholder={placeholder}
            error={hasError}
            helperText={displayHelperText}
            disabled={disabled}
            required={required}
            fullWidth={fullWidth}
            multiline={multiline}
            {...(rows !== undefined && { rows })}
            {...(maxRows !== undefined && { maxRows })}
            type={type}
            {...(autoComplete && { autoComplete })}
            variant={variant}
            size={size}
            margin={margin}
            inputProps={inputProps}
            InputProps={{
              startAdornment,
              endAdornment,
              ...textFieldProps.InputProps,
            }}
            InputLabelProps={{
              shrink:
                !!field.value ||
                !!placeholder ||
                type === 'date' ||
                type === 'datetime-local' ||
                type === 'time',
              ...textFieldProps.InputLabelProps,
            }}
          />
        )
      }}
    />
  )
}

/**
 * Specialized text area component
 */
export function FormTextArea<T extends FieldValues>(
  props: Omit<FormTextFieldProps<T>, 'multiline' | 'type'>,
) {
  return <FormTextField {...props} multiline rows={4} maxRows={10} />
}

/**
 * Password field with show/hide toggle
 */
export function FormPasswordField<T extends FieldValues>({
  ...props
}: Omit<FormTextFieldProps<T>, 'type' | 'endAdornment'>) {
  const [showPassword, setShowPassword] = useState(false)

  const togglePasswordVisibility = () => {
    setShowPassword(prev => !prev)
  }

  return (
    <FormTextField
      {...props}
      type={showPassword ? 'text' : 'password'}
      endAdornment={
        <button
          type="button"
          onClick={togglePasswordVisibility}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '4px',
          }}
        >
          {showPassword ? '🙈' : '👁️'}
        </button>
      }
    />
  )
}
