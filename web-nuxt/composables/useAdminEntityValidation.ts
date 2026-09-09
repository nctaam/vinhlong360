import { ref, type Ref } from 'vue'

export interface UseAdminEntityValidationOptions {
  form: Ref<{ id: string; name: string; type: string }>
  editingEntity: Ref<unknown>
}

export function useAdminEntityValidation(options: UseAdminEntityValidationOptions) {
  const { form, editingEntity } = options
  const fieldErrors = ref<Record<string, string>>({})

  function clearFieldError(key: string) {
    if (fieldErrors.value[key]) {
      const next = { ...fieldErrors.value }
      delete next[key]
      fieldErrors.value = next
    }
  }

  function validateForm(): boolean {
    const errs: Record<string, string> = {}
    if (!String(form.value.name || '').trim()) errs.name = 'Tên không được để trống'
    if (!editingEntity.value && !String(form.value.id || '').trim()) errs.id = 'ID không được để trống'
    if (!editingEntity.value && form.value.id && !/^[a-z0-9\-_]+$/.test(String(form.value.id))) {
      errs.id = 'ID chỉ chứa chữ thường, số, dấu gạch'
    }
    if (!form.value.type) errs.type = 'Loại không được để trống'
    fieldErrors.value = errs
    return Object.keys(errs).length === 0
  }

  function resetFieldErrors() {
    fieldErrors.value = {}
  }

  return {
    fieldErrors,
    clearFieldError,
    validateForm,
    resetFieldErrors,
  }
}
