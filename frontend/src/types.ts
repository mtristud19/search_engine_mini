export type Category = { id: number; name: string; slug: string };
export type Document = {
  id: string;
  title: string;
  content: string;
  category: Category | null;
  tags: string[];
  author: string;
  is_published: boolean;
  view_count: number;
  created_at: string;
  updated_at: string;
};
export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
export type SearchResult = {
  id: string;
  title: string;
  snippet: string;
  category: string | null;
  tags: string[];
};
export type SearchResponse = {
  count: number;
  did_you_mean?: boolean;
  results: SearchResult[];
};
export type ApiError = { message: string; fields?: Record<string, string[]> };
