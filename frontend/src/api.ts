import type {
  ApiError,
  Category,
  Document,
  Page,
  SearchResponse,
  SearchResult,
} from "./types";

const base = import.meta.env.VITE_API_BASE_URL || "/api";
const credentials = () => sessionStorage.getItem("signals.basic");
export const setCredentials = (username: string, password: string) =>
  sessionStorage.setItem("signals.basic", btoa(`${username}:${password}`));
export const clearCredentials = () =>
  sessionStorage.removeItem("signals.basic");
export const isSignedIn = () => Boolean(credentials());

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  const basic = credentials();
  if (basic) headers.set("Authorization", `Basic ${basic}`);
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers,
    signal: init.signal,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const fields =
      typeof body === "object" ? (body as Record<string, string[]>) : undefined;
    throw {
      message:
        body.detail ||
        body.error ||
        (response.status === 401
          ? "Your credentials were not accepted."
          : "The request could not be completed."),
      fields,
    } as ApiError;
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
const query = (values: Record<string, string | number | undefined>) => {
  const p = new URLSearchParams();
  Object.entries(values).forEach(
    ([k, v]) => v !== undefined && v !== "" && p.set(k, String(v)),
  );
  const s = p.toString();
  return s ? `?${s}` : "";
};
export const api = {
  documents: (p: Record<string, string | number | undefined> = {}) =>
    request<Page<Document>>(`/documents/${query(p)}`),
  document: (id: string) => request<Document>(`/documents/${id}/`),
  categories: (p: Record<string, string | number | undefined> = {}) =>
    request<Page<Category> | Category[]>(`/categories/${query(p)}`),
  createCategory: (data: Pick<Category, "name" | "slug">) =>
    request<Category>("/categories/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCategory: (id: number, data: Pick<Category, "name" | "slug">) =>
    request<Category>(`/categories/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  removeCategory: (id: number) =>
    request<void>(`/categories/${id}/`, { method: "DELETE" }),
  search: (p: Record<string, string | number | undefined>) =>
    request<SearchResponse>(`/search/${query(p)}`),
  suggestions: (q: string) =>
    request<{ suggestions: string[] }>(`/search/suggest/${query({ q })}`),
  related: (id: string) =>
    request<{ results: SearchResult[] }>(`/documents/${id}/similar/`),
  create: (data: Partial<Document> & { category_id?: number }) =>
    request<Document>("/documents/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<Document> & { category_id?: number }) =>
    request<Document>(`/documents/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  remove: (id: string) =>
    request<void>(`/documents/${id}/`, { method: "DELETE" }),
};
