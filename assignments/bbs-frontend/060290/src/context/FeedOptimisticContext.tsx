import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import type { Post } from '../types/bbs'

type FeedOptimisticContextValue = {
  optimisticPost: Post | null
  setOptimisticPost: (post: Post | null) => void
  registerFeedRefetch: (fn: () => void | Promise<void>) => () => void
  refetchFeed: () => Promise<void>
}

const FeedOptimisticContext = createContext<FeedOptimisticContextValue | null>(null)

export function FeedOptimisticProvider({ children }: { children: ReactNode }) {
  const [optimisticPost, setOptimisticPost] = useState<Post | null>(null)
  const refetchRef = useRef<(() => void | Promise<void>) | null>(null)

  const registerFeedRefetch = useCallback((fn: () => void | Promise<void>) => {
    refetchRef.current = fn
    return () => {
      if (refetchRef.current === fn) {
        refetchRef.current = null
      }
    }
  }, [])

  const refetchFeed = useCallback(async () => {
    await refetchRef.current?.()
  }, [])

  const value = useMemo(
    () => ({
      optimisticPost,
      setOptimisticPost: setOptimisticPost,
      registerFeedRefetch,
      refetchFeed,
    }),
    [optimisticPost, registerFeedRefetch, refetchFeed],
  )

  return (
    <FeedOptimisticContext.Provider value={value}>{children}</FeedOptimisticContext.Provider>
  )
}

/** Context consumer; co-located with provider. */
// eslint-disable-next-line react-refresh/only-export-components -- hook + provider pattern
export function useFeedOptimistic(): FeedOptimisticContextValue {
  const ctx = useContext(FeedOptimisticContext)
  if (!ctx) {
    throw new Error('useFeedOptimistic must be used within FeedOptimisticProvider')
  }
  return ctx
}
