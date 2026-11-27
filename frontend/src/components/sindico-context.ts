import { createContext, useContext } from "react";
import type { Sindico } from "@/lib/auth";

export const SindicoContext = createContext<Sindico | null>(null);

export function useSindico() {
  return useContext(SindicoContext);
}
