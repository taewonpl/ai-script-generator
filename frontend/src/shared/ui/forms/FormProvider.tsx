import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useState,
  useRef,
} from 'react'
import type { ReactNode } from 'react'
import type { UseFormReturn, FieldValues, DefaultValues } from 'react-hook-form'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { ZodSchema } from 'zod'
import { useToastHelpers } from '@/shared/ui/components/toast'
import type {
  FormOptions,
  FormProviderConfig,
  AutoSaveData,
  FormFieldError,
} from './types'

interface FormContextValue<T extends FieldValues> {
  form: UseFormReturn<T>
  control: UseFormReturn<T>['control']
  watch: UseFormReturn<T>['watch']
  isSubmitting: boolean
  isDirty: boolean
  hasUnsavedChanges: boolean
  autoSaveStatus: 'idle' | 'saving' | 'saved' | 'error'
  lastAutoSaveTime: Date | null
  submitForm: () => Promise<void>
  resetForm: () => void
  loadAutoSavedData: () => boolean
  clearAutoSavedData: () => void
}

const FormContext = createContext<FormContextValue<any> | undefined>(undefined)

interface FormProviderProps<T extends FieldValues> {
  children: ReactNode
  schema: ZodSchema<T>
  defaultValues?: DefaultValues<T>
  onSubmit: (data: T) => Promise<void> | void
  onError?: (errors: FormFieldError[]) => void
  options?: FormOptions
  config?: FormProviderConfig
}

/**
 * Enhanced form provider with auto-save, validation, and error handling
 *
 * Features:
 * - React Hook Form + Zod integration
 * - Auto-save to localStorage
 * - Server error mapping
 * - Form dirty state tracking
 * - Page leave confirmation
 * - Toast notifications
 */
export function FormProvider<T extends FieldValues>({
  children,
  schema,
  defaultValues,
  onSubmit,
  onError,
  options = {},
  config = {},
}: FormProviderProps<T>) {
  const {
    autoSave = false,
    autoSaveKey = 'form-autosave',
    autoSaveDelay = 1000,
    confirmOnLeave = true,
    resetOnSuccess = true,
  } = options

  const {
    showErrorToasts = true,
    validateOnChange = true,
    validateOnBlur = true,
  } = config

  const { showError, showSuccess, showInfo } = useToastHelpers()

  // Form state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [autoSaveStatus, setAutoSaveStatus] = useState<
    'idle' | 'saving' | 'saved' | 'error'
  >('idle')
  const [lastAutoSaveTime, setLastAutoSaveTime] = useState<Date | null>(null)
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)

  // Initialize form
  const form = useForm<T>({
    // @ts-expect-error - Zod schema type compatibility with RHF generics
    resolver: zodResolver(schema),
    defaultValues,
    mode: validateOnChange
      ? 'onChange'
      : validateOnBlur
        ? 'onBlur'
        : 'onSubmit',
  })

  // Watch form values for auto-save
  const watchedValues = useWatch({ control: form.control })
  const isDirty = form.formState.isDirty
  const hasUnsavedChanges = isDirty || autoSaveStatus === 'saving'

  // Auto-save functionality
  const saveToLocalStorage = useCallback(
    (data: T) => {
      if (!autoSave || !autoSaveKey) return

      try {
        const autoSaveData: AutoSaveData = {
          values: data,
          timestamp: Date.now(),
          version: '1.0',
        }
        localStorage.setItem(autoSaveKey, JSON.stringify(autoSaveData))
        setAutoSaveStatus('saved')
        setLastAutoSaveTime(new Date())
      } catch (error) {
        console.error('Failed to auto-save form data:', error)
        setAutoSaveStatus('error')
      }
    },
    [autoSave, autoSaveKey],
  )

  // Load auto-saved data
  const loadAutoSavedData = useCallback((): boolean => {
    if (!autoSave || !autoSaveKey) return false

    try {
      const saved = localStorage.getItem(autoSaveKey)
      if (!saved) return false

      const autoSaveData: AutoSaveData = JSON.parse(saved)

      // Check if data is not too old (24 hours)
      const maxAge = 24 * 60 * 60 * 1000
      if (Date.now() - autoSaveData.timestamp > maxAge) {
        clearAutoSavedData()
        return false
      }

      // Validate saved data against schema
      const validationResult = schema.safeParse(autoSaveData.values)
      if (!validationResult.success) {
        clearAutoSavedData()
        return false
      }

      // @ts-expect-error Complex generic type resolution with form reset
      form.reset(autoSaveData.values)
      setLastAutoSaveTime(new Date(autoSaveData.timestamp))
      showInfo('이전에 저장된 데이터를 불러왔습니다.')
      return true
    } catch (error) {
      console.error('Failed to load auto-saved data:', error)
      clearAutoSavedData()
      return false
    }
  }, [autoSave, autoSaveKey, schema, form, showInfo])

  // Clear auto-saved data
  const clearAutoSavedData = useCallback(() => {
    if (!autoSaveKey) return

    localStorage.removeItem(autoSaveKey)
    setAutoSaveStatus('idle')
    setLastAutoSaveTime(null)
  }, [autoSaveKey])

  // Auto-save effect
  useEffect(() => {
    if (!autoSave || !isDirty) return

    // Clear existing timeout
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }

    setAutoSaveStatus('saving')

    // Debounced auto-save
    autoSaveTimeoutRef.current = setTimeout(() => {
      const currentValues = form.getValues()
      saveToLocalStorage(currentValues)
    }, autoSaveDelay)

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
      }
    }
  }, [
    watchedValues,
    autoSave,
    isDirty,
    autoSaveDelay,
    form,
    saveToLocalStorage,
  ])

  // Page leave confirmation
  useEffect(() => {
    if (!confirmOnLeave) return

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue =
          '저장되지 않은 변경사항이 있습니다. 페이지를 떠나시겠습니까?'
        return e.returnValue
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [confirmOnLeave, hasUnsavedChanges])

  // Submit handler
  const submitForm = useCallback(async () => {
    setIsSubmitting(true)

    try {
      const isValid = await form.trigger()
      if (!isValid) {
        const errors = Object.entries(form.formState.errors).map(
          ([field, error]) => ({
            field,
            message: (error?.message as string) || '유효하지 않은 값입니다',
          }),
        ) as FormFieldError[]

        if (showErrorToasts) {
          showError('입력 내용을 확인해주세요.')
        }

        onError?.(errors)
        return
      }

      const data = form.getValues()
      await onSubmit(data)

      if (resetOnSuccess) {
        form.reset(defaultValues)
      }

      if (autoSave) {
        clearAutoSavedData()
      }

      showSuccess('저장되었습니다.')
    } catch (error: unknown) {
      console.error('Form submission error:', error)

      // Handle server validation errors
      // @ts-expect-error Server error response handling
      if (error?.response?.data?.errors) {
        const serverErrors = (
          error as { response?: { data?: { errors?: Record<string, string> } } }
        )?.response?.data?.errors
        Object.entries(serverErrors || {}).forEach(([field, message]) => {
          form.setError(field as any, { message: message })
        })
      }

      if (showErrorToasts) {
        showError((error as any)?.message || '저장 중 오류가 발생했습니다.')
      }

      const formErrors: FormFieldError[] = Object.entries(
        form.formState.errors,
      ).map(([field, error]) => ({
        field,
        message: (error?.message as string) || '오류가 발생했습니다',
      })) as FormFieldError[]

      onError?.(formErrors)
    } finally {
      setIsSubmitting(false)
    }
  }, [
    form,
    onSubmit,
    onError,
    resetOnSuccess,
    autoSave,
    showErrorToasts,
    showError,
    showSuccess,
    clearAutoSavedData,
  ])

  // Reset form
  const resetForm = useCallback(() => {
    form.reset()
    if (autoSave) {
      clearAutoSavedData()
    }
  }, [form, autoSave, clearAutoSavedData])

  // Load auto-saved data on mount
  useEffect(() => {
    if (autoSave) {
      loadAutoSavedData()
    }
  }, [autoSave, loadAutoSavedData])

  const contextValue: FormContextValue<T> = {
    form: form as any /* RHF generic type compatibility */,
    control: form.control as any,
    watch: form.watch,
    isSubmitting,
    isDirty,
    hasUnsavedChanges,
    autoSaveStatus,
    lastAutoSaveTime,
    submitForm,
    resetForm,
    loadAutoSavedData,
    clearAutoSavedData,
  }

  return (
    <FormContext.Provider value={contextValue as any}>
      {children}
    </FormContext.Provider>
  )
}

/**
 * Hook to access form context
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useFormContext<
  T extends FieldValues = FieldValues,
>(): FormContextValue<T> {
  const context = useContext(FormContext)

  if (!context) {
    throw new Error('useFormContext must be used within a FormProvider')
  }

  return context
}

/**
 * Hook for form field registration with enhanced features
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useFormField<T extends FieldValues = FieldValues>(
  name: keyof T,
) {
  const { form } = useFormContext<T>()

  const fieldState = form.getFieldState(name as any)
  const error = fieldState.error

  return {
    field: form.register(name as any),
    fieldState,
    hasError: !!error,
    errorMessage: error?.message as string,
    value: form.watch(name as any),
    setValue: (value: T[keyof T]) => form.setValue(name as any, value),
    clearError: () => form.clearErrors(name as any),
  }
}
