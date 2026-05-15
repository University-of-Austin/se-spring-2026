import { listUsers } from "../api/endpoints";
import { useApi } from "./useApi";

export function useUsers() {
  return useApi((signal) => listUsers(signal), []);
}
