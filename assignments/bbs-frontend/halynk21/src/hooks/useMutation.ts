import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';

// onMutate may return a rollback callback that runs on failure. This is how
// optimistic mutations restore state when the server rejects.
export type MutationOptions<TArg, TResult> = {
  onMutate?: (arg: TArg) => void | { rollback: () => void };
  onSuccess?: (result: TResult, arg: TArg) => void;
  onError?: (error: ApiError, arg: TArg) => void;
};

export type MutationResult<TArg, TResult> = {
  mutate: (arg: TArg) => Promise<TResult | undefined>;
  isPending: boolean;
  error: ApiError | null;
  reset: () => void;
};

export function useMutation<TArg, TResult>(
  mutator: (arg: TArg) => Promise<TResult>,
  options: MutationOptions<TArg, TResult> = {},
): MutationResult<TArg, TResult> {
  const [isPending, setIsPending] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  const optsRef = useRef(options);
  const mutatorRef = useRef(mutator);
  useEffect(() => {
    optsRef.current = options;
    mutatorRef.current = mutator;
  });

  const mutate = useCallback(async (arg: TArg): Promise<TResult | undefined> => {
    setIsPending(true);
    setError(null);

    let rollback: (() => void) | undefined;
    const onMutateResult = optsRef.current.onMutate?.(arg);
    if (
      onMutateResult &&
      typeof onMutateResult === 'object' &&
      'rollback' in onMutateResult &&
      typeof onMutateResult.rollback === 'function'
    ) {
      rollback = onMutateResult.rollback;
    }

    try {
      const result = await mutatorRef.current(arg);
      optsRef.current.onSuccess?.(result, arg);
      return result;
    } catch (err) {
      const apiErr =
        err instanceof ApiError
          ? err
          : new ApiError(0, err instanceof Error ? err.message : 'Unknown error');
      rollback?.();
      setError(apiErr);
      optsRef.current.onError?.(apiErr, arg);
      return undefined;
    } finally {
      setIsPending(false);
    }
  }, []);

  // Lets a form clear stale server errors when the user starts editing
  // again, without affecting an in-flight request.
  const reset = useCallback(() => {
    setError(null);
  }, []);

  return { mutate, isPending, error, reset };
}
