/**
 * Form system types and interfaces
 */

import type { Control, FieldValues, Path, UseFormReturn } from 'react-hook-form'

export interface BaseFormProps<T extends FieldValues> {
  control: Control<T>
  name: Path<T>
  label?: string
  helperText?: string
  disabled?: boolean
  required?: boolean
  fullWidth?: boolean
}

export interface FormFieldError {
  field: string
  message: string
  code?: string
}

export interface FormOptions {
  autoSave?: boolean
  autoSaveKey?: string
  autoSaveDelay?: number
  confirmOnLeave?: boolean
  resetOnSuccess?: boolean
}

export interface FormProviderConfig {
  showErrorToasts?: boolean
  autoFocus?: boolean
  validateOnChange?: boolean
  validateOnBlur?: boolean
}

export interface AutoSaveData {
  values: FieldValues
  timestamp: number
  version: string
}

export interface FormSubmitContext<T extends FieldValues = FieldValues> {
  values: T
  formMethods: UseFormReturn<T>
  setError: (field: keyof T, error: { message: string; type?: string }) => void
  clearErrors: () => void
}
