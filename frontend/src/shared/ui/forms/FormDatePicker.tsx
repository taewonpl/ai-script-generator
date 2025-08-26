import { Controller } from 'react-hook-form'
import type { FieldValues } from 'react-hook-form'
import { TextField, FormControl, FormHelperText } from '@mui/material'
import type { BaseFormProps } from './types'
import { useFormContext } from './FormProvider'

export interface FormDatePickerProps<T extends FieldValues>
  extends BaseFormProps<T> {
  placeholder?: string
  minDate?: string
  maxDate?: string
  type?: 'date' | 'datetime-local' | 'time'
  format?: string
}

/**
 * HTML5 Date/Time picker integrated with React Hook Form
 *
 * Features:
 * - Date, datetime, and time selection
 * - Min/max date constraints
 * - Error state handling
 * - Custom formatting
 *
 * Note: For advanced date picking, consider integrating with:
 * - @mui/x-date-pickers (Material-UI date pickers)
 * - react-datepicker
 * - date-fns for formatting
 */
export function FormDatePicker<T extends FieldValues>({
  control,
  name,
  label,
  placeholder,
  helperText,
  disabled = false,
  required = false,
  fullWidth = true,
  minDate,
  maxDate,
  type = 'date',
  format,
}: FormDatePickerProps<T>) {
  // Using control prop instead of form context for better type safety

  // Format date value for input
  const formatDateValue = (value: unknown) => {
    if (!value) return ''

    try {
      if (typeof value === 'string' && value.includes('T')) {
        // ISO string
        const date = new Date(value)
        if (type === 'date') {
          return date.toISOString().split('T')[0]
        } else if (type === 'datetime-local') {
          return date.toISOString().slice(0, 16)
        } else if (type === 'time') {
          return date.toTimeString().slice(0, 5)
        }
      }
      return value
    } catch {
      return value
    }
  }

  // Parse input value to Date
  const parseDateValue = (value: string) => {
    if (!value) return null

    try {
      if (type === 'date') {
        return new Date(value + 'T00:00:00')
      } else if (type === 'datetime-local') {
        return new Date(value)
      } else if (type === 'time') {
        const today = new Date().toISOString().split('T')[0]
        return new Date(`${today}T${value}:00`)
      }
      return new Date(value)
    } catch {
      return null
    }
  }

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => {
        const hasError = !!fieldState.error
        const errorMessage = fieldState.error?.message
        const displayHelperText = errorMessage || helperText

        return (
          <FormControl fullWidth={fullWidth} error={hasError} margin="normal">
            <TextField
              label={label}
              type={type}
              value={formatDateValue(field.value)}
              onChange={event => {
                const inputValue = event.target.value
                const parsedValue = parseDateValue(inputValue)
                field.onChange(format ? inputValue : parsedValue)
              }}
              onBlur={field.onBlur}
              placeholder={placeholder}
              disabled={disabled}
              required={required}
              fullWidth={fullWidth}
              error={hasError}
              variant="outlined"
              size="medium"
              inputProps={{
                min: minDate,
                max: maxDate,
              }}
              InputLabelProps={{
                shrink: true,
              }}
            />
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
 * DateTime picker variant
 */
export function FormDateTimePicker<T extends FieldValues>(
  props: Omit<FormDatePickerProps<T>, 'type'>,
) {
  return <FormDatePicker {...props} type="datetime-local" />
}

/**
 * Time picker variant
 */
export function FormTimePicker<T extends FieldValues>(
  props: Omit<FormDatePickerProps<T>, 'type'>,
) {
  return <FormDatePicker {...props} type="time" />
}

/**
 * Date range picker (two date inputs)
 */
export interface FormDateRangePickerProps<T extends FieldValues> {
  startDateName: keyof T
  endDateName: keyof T
  startLabel?: string
  endLabel?: string
  helperText?: string
  disabled?: boolean
  required?: boolean
  fullWidth?: boolean
}

export function FormDateRangePicker<T extends FieldValues>({
  startDateName,
  endDateName,
  startLabel = '시작 날짜',
  endLabel = '종료 날짜',
  helperText,
  disabled = false,
  required = false,
  fullWidth = true,
}: FormDateRangePickerProps<T>) {
  const { form } = useFormContext<T>()

  const startValue = form.watch(startDateName as any)
  const endValue = form.watch(endDateName as any)

  return (
    <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
      {/* @ts-expect-error - control prop type mismatch with RHF generic constraints */}
      <FormDatePicker
        name={startDateName as any}
        label={startLabel}
        disabled={disabled}
        required={required}
        fullWidth={fullWidth}
        maxDate={
          endValue
            ? new Date(endValue as any).toISOString().split('T')[0]
            : undefined
        }
      />
      {/* @ts-expect-error - control prop type mismatch with RHF generic constraints */}
      <FormDatePicker
        name={endDateName as any}
        label={endLabel}
        disabled={disabled}
        required={required}
        fullWidth={fullWidth}
        minDate={
          startValue
            ? new Date(startValue as any).toISOString().split('T')[0]
            : undefined
        }
        helperText={helperText}
      />
    </div>
  )
}
