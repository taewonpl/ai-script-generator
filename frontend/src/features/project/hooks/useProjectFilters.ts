/**
 * Project filters hook - temporary placeholder
 */

export interface ProjectFilters {
  search?: string
  status?: string
  type?: string
}

export function useProjectFilters() {
  // Temporary implementation to resolve missing export
  return {
    filters: {} as ProjectFilters,
    setFilters: () => {},
    clearFilters: () => {},
  }
}
