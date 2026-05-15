export type AsyncState<T> =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'success'; data: T }
  | {
      phase: 'error'
      message: string
      httpStatus?: number
      body?: unknown
    }
