import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { api, clearCredentials, isSignedIn, setCredentials } from "./api";
import type {
  Category,
  Document,
  Page,
  SearchResponse,
  SearchResult,
} from "./types";
import "./styles.css";
import "./public.css";
import "./admin.css";

const date = (value: string) =>
  new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(
    new Date(value),
  );
const words = (text: string) =>
  `${Math.max(1, Math.ceil(text.trim().split(/\s+/).length / 220))} min read`;
function useLoad<T>(work: () => Promise<T>, deps: React.DependencyList) {
  const [state, set] = useState<{ data?: T; error?: string; loading: boolean }>(
    { loading: true },
  );
  useEffect(() => {
    let live = true;
    set({ loading: true });
    work()
      .then((data) => live && set({ data, loading: false }))
      .catch(
        (e) =>
          live &&
          set({ error: e.message || "Something went wrong.", loading: false }),
      );
    return () => {
      live = false;
    };
  }, deps);
  return state;
}
function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header>
      <div className="bar">
        <Link className="brand" to="/">
          SIGNALS<span>.</span>
        </Link>
        <button
          className="menu"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label="Toggle navigation"
        >
          Menu
        </button>
        <nav className={open ? "show" : ""}>
          <NavLink to="/blog">All articles</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/admin">Editor desk</NavLink>
        </nav>
      </div>
    </header>
  );
}
function Layout({ children }: React.PropsWithChildren) {
  return (
    <>
      <Header />
      <main>{children}</main>
      <footer>
        <span>SIGNALS · Technology editorial</span>
        <span>Built for clearer thinking.</span>
      </footer>
    </>
  );
}
function State({
  loading,
  error,
  empty,
}: {
  loading?: boolean;
  error?: string;
  empty?: string;
}) {
  return (
    <div className="state" role={error ? "alert" : undefined}>
      {loading ? "Loading articles…" : error || empty}
    </div>
  );
}
function ConfirmDialog({
  title,
  detail,
  onCancel,
  onConfirm,
}: {
  title: string;
  detail: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="dialog-backdrop" role="presentation">
      <div
        className="dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
      >
        <h2 id="dialog-title">{title}</h2>
        <p>{detail}</p>
        <div>
          <button className="secondary-button" onClick={onCancel}>
            Cancel
          </button>
          <button className="danger-button" onClick={onConfirm}>
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
function Card({ doc }: { doc: Document }) {
  return (
    <article className="card">
      <div className="eyebrow">{doc.category?.name || "Technology"}</div>
      <h3>
        <Link to={`/blog/${doc.id}`}>{doc.title}</Link>
      </h3>
      <p>
        {doc.content.slice(0, 160)}
        {doc.content.length > 160 ? "…" : ""}
      </p>
      <div className="meta">
        By {doc.author} · {date(doc.created_at)} · {words(doc.content)}
      </div>
      {doc.tags.length > 0 && (
        <div className="tags">
          {doc.tags.slice(0, 3).map((t) => (
            <Link key={t} to={`/tags/${encodeURIComponent(t)}`}>
              #{t}
            </Link>
          ))}
        </div>
      )}
    </article>
  );
}
function Pager({
  page,
  setPage,
}: {
  page: Page<unknown>;
  setPage: (n: number) => void;
}) {
  const next = page.next
    ? Number(new URL(page.next).searchParams.get("page"))
    : undefined;
  const previous = page.previous
    ? Number(new URL(page.previous).searchParams.get("page"))
    : undefined;
  const n = previous ? previous + 1 : next ? next - 1 : 1;
  return (
    <nav className="pager" aria-label="Pagination">
      <button
        disabled={!page.previous}
        onClick={() => setPage(Math.max(1, n - 1))}
      >
        Previous
      </button>
      <span>Page {n}</span>
      <button disabled={!page.next} onClick={() => setPage(n + 1)}>
        Next
      </button>
    </nav>
  );
}
function Home() {
  const latest = useLoad(
    () => api.documents({ page: 1, ordering: "-created_at" }),
    [],
  );
  const trending = useLoad(
    () => api.documents({ page: 1, ordering: "-view_count" }),
    [],
  );
  const docs = latest.data?.results || [];
  return (
    <Layout>
      <section className="hero">
        <p className="eyebrow">Independent technology publication</p>
        <h1>
          Ideas worth <em>building</em> on.
        </h1>
        <p className="lede">
          Practical notes on search, systems, and the work behind resilient
          software.
        </p>
        <Link className="button" to="/blog">
          Explore the archive
        </Link>
      </section>
      {latest.loading || latest.error ? (
        <State loading={latest.loading} error={latest.error} />
      ) : docs.length ? (
        <>
          <section className="featured">
            <Card doc={docs[0]} />
            <div>
              <p className="eyebrow">Editor’s note</p>
              <h2>Good tools deserve good explanations.</h2>
              <p>
                Signals collects the implementation detail that makes technology
                useful.
              </p>
            </div>
          </section>
          <section>
            <div className="section-head">
              <h2>Latest dispatches</h2>
              <Link to="/blog">View all →</Link>
            </div>
            <div className="grid">
              {docs.slice(1).map((d) => (
                <Card key={d.id} doc={d} />
              ))}
            </div>
          </section>
        </>
      ) : (
        <State empty="No published articles yet." />
      )}
      {trending.data?.results.length ? (
        <section>
          <div className="section-head">
            <h2>Most read</h2>
          </div>
          <div className="compact">
            {trending.data.results.slice(0, 3).map((d, i) => (
              <Link key={d.id} to={`/blog/${d.id}`}>
                <b>0{i + 1}</b>
                {d.title}
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </Layout>
  );
}
function Listing({ category, tag }: { category?: string; tag?: string }) {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const page = Number(params.get("page") || 1);
  const [q, setQ] = useState("");
  const categories = useLoad(() => api.categories(), []);
  const result = useLoad(
    () => api.documents({ page, category, tag, ordering: "-created_at" }),
    [page, category, tag],
  );
  const categoryList = Array.isArray(categories.data)
    ? categories.data
    : categories.data?.results || [];
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = q.trim();
    if (query) navigate(`/search?q=${encodeURIComponent(query)}`);
  };
  const title = category
    ? category.replace(/-/g, " ")
    : tag
      ? `#${tag}`
      : "The archive";
  return (
    <Layout>
      <section className="page-title">
        <p className="eyebrow">
          {category ? "Category" : tag ? "Topic" : "All articles"}
        </p>
        <h1>{title}</h1>
        <p>
          {category
            ? "A focused collection of published articles."
            : tag
              ? "Published articles sharing this topic."
              : "Reporting and working notes from the software frontier."}
        </p>
      </section>
      {!category && !tag && (
        <>
          <form className="search-form" onSubmit={submit}>
            <label htmlFor="blog-search" className="sr">
              Search articles
            </label>
            <input
              id="blog-search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search the archive"
            />
            <button>Search</button>
          </form>
          <div className="filters">
            <Link to="/blog">All</Link>
            {categoryList.map((c) => (
              <Link key={c.id} to={`/categories/${c.slug}`}>
                {c.name}
              </Link>
            ))}
          </div>
        </>
      )}
      {result.loading || result.error ? (
        <State loading={result.loading} error={result.error} />
      ) : result.data && result.data.results.length ? (
        <>
          <div className="grid">
            {result.data.results.map((d) => (
              <Card key={d.id} doc={d} />
            ))}
          </div>
          <Pager
            page={result.data}
            setPage={(next) =>
              setParams(next > 1 ? { page: String(next) } : {})
            }
          />
        </>
      ) : (
        <State empty="No published articles match this selection." />
      )}
    </Layout>
  );
}
function Article() {
  const { id = "" } = useParams();
  const item = useLoad(() => api.document(id), [id]);
  const related = useLoad(() => api.related(id), [id]);
  const [copied, setCopied] = useState(false);
  const [shareError, setShareError] = useState("");
  if (item.loading || item.error)
    return (
      <Layout>
        <State
          loading={item.loading}
          error={item.error || "This article is unavailable."}
        />
      </Layout>
    );
  const d = item.data!;
  const share = async () => {
    const data = { title: d.title, url: window.location.href };
    try {
      if (navigator.share) {
        await navigator.share(data);
      } else {
        await navigator.clipboard.writeText(data.url);
        setCopied(true);
      }
    } catch {
      setShareError(
        "Unable to share this article. Copy the page address from your browser instead.",
      );
    }
  };
  return (
    <Layout>
      <article className="article">
        <Link className="back" to="/blog">
          ← Back to archive
        </Link>
        <p className="eyebrow">{d.category?.name || "Technology"}</p>
        <h1>{d.title}</h1>
        <div className="article-meta">
          By {d.author} · Published {date(d.created_at)} · {words(d.content)}
        </div>
        <div className="article-actions">
          <button onClick={share}>Share{copied ? " — link copied" : ""}</button>
          {shareError && (
            <p className="form-error" role="status">
              {shareError}
            </p>
          )}
        </div>
        <div className="article-body">
          {d.content.split(/\n{2,}/).map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
        {d.tags.length ? (
          <div className="tags">
            {d.tags.map((t) => (
              <Link key={t} to={`/tags/${encodeURIComponent(t)}`}>
                #{t}
              </Link>
            ))}
          </div>
        ) : null}
        {related.data?.results.length ? (
          <section className="related">
            <h2>Continue reading</h2>
            {related.data.results.map((r) => (
              <Link key={r.id} to={`/blog/${r.id}`}>
                {r.title}
              </Link>
            ))}
          </section>
        ) : null}
      </article>
    </Layout>
  );
}
function Search() {
  const [params, setParams] = useSearchParams();
  const activeQ = params.get("q") || "";
  const [q, setQ] = useState(activeQ);
  const page = Number(params.get("page") || 1);
  const result = useLoad(
    () =>
      activeQ
        ? api.search({ q: activeQ, page })
        : Promise.resolve<SearchResponse>({ count: 0, results: [] }),
    [activeQ, page],
  );
  const suggestions = useLoad(
    () =>
      q.trim().length > 1
        ? api.suggestions(q.trim())
        : Promise.resolve({ suggestions: [] }),
    [q],
  );
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setParams(q.trim() ? { q: q.trim() } : {});
  };
  const totalPages = Math.ceil((result.data?.count || 0) / 10);
  return (
    <Layout>
      <section className="page-title">
        <p className="eyebrow">Search</p>
        <h1>Find a signal</h1>
      </section>
      <form className="search-form search-with-suggestions" onSubmit={submit}>
        <label htmlFor="search" className="sr">
          Search articles
        </label>
        <input
          id="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Elasticsearch, Django, systems…"
          autoComplete="off"
        />
        {q !== activeQ && suggestions.data?.suggestions.length ? (
          <div className="suggestions" role="listbox">
            {suggestions.data.suggestions.map((value) => (
              <button
                type="button"
                role="option"
                key={value}
                onClick={() => {
                  setQ(value);
                  setParams({ q: value });
                }}
              >
                {value}
              </button>
            ))}
          </div>
        ) : null}
        <button>Search</button>
      </form>
      {activeQ &&
        (result.loading || result.error ? (
          <State loading={result.loading} error={result.error} />
        ) : (
          <section>
            <p className="results-count">
              {result.data?.count || 0} results for “{activeQ}”
            </p>
            {result.data?.did_you_mean && (
              <p className="search-note">
                Showing close matches for this query.
              </p>
            )}
            <div className="results">
              {result.data?.results.map((r) => (
                <article key={r.id}>
                  <p className="eyebrow">{r.category || "Technology"}</p>
                  <h2>
                    <Link to={`/blog/${r.id}`}>{r.title}</Link>
                  </h2>
                  <p>{r.snippet.replace(/<[^>]*>/g, "")}</p>
                </article>
              ))}
            </div>
            {!result.data?.results.length && (
              <State empty="Try a different search term." />
            )}
            {totalPages > 1 && (
              <nav className="pager" aria-label="Search pages">
                <button
                  disabled={page === 1}
                  onClick={() =>
                    setParams({ q: activeQ, page: String(page - 1) })
                  }
                >
                  Previous
                </button>
                <span>
                  Page {page} of {totalPages}
                </span>
                <button
                  disabled={page >= totalPages}
                  onClick={() =>
                    setParams({ q: activeQ, page: String(page + 1) })
                  }
                >
                  Next
                </button>
              </nav>
            )}
          </section>
        ))}
    </Layout>
  );
}
function AdminShell({ children }: React.PropsWithChildren) {
  const nav = useNavigate();
  return (
    <div className="admin">
      <aside>
        <Link className="brand" to="/admin">
          SIGNALS<span>.</span>
        </Link>
        <NavLink end to="/admin">
          Overview
        </NavLink>
        <NavLink to="/admin/posts">Articles</NavLink>
        <NavLink to="/admin/categories">Categories</NavLink>
        <Link to="/">View site ↗</Link>
        <button
          onClick={() => {
            clearCredentials();
            nav("/admin/login");
          }}
        >
          Sign out
        </button>
      </aside>
      <main>{children}</main>
    </div>
  );
}
function Login() {
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password)
      return setError("Enter your username and password.");
    setCredentials(username, password);
    nav("/admin");
  };
  return (
    <div className="login">
      <Link className="brand" to="/">
        SIGNALS<span>.</span>
      </Link>
      <form onSubmit={submit}>
        <p className="eyebrow">Editor access</p>
        <h1>Welcome back.</h1>
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button>Continue</button>
        <p className="small">
          The verified API uses Basic authentication but exposes no login or
          current-user endpoint. Credentials are retained only for this browser
          session and are verified by protected mutations.
        </p>
      </form>
    </div>
  );
}
function Protected({ children }: React.PropsWithChildren) {
  return isSignedIn() ? (
    <>{children}</>
  ) : (
    <Navigate to="/admin/login" replace />
  );
}
function Dashboard() {
  const docs = useLoad(() => api.documents({ page: 1 }), []);
  const categories = useLoad(() => api.categories(), []);
  const all = docs.data?.results || [];
  const cats = Array.isArray(categories.data)
    ? categories.data.length
    : categories.data?.count || 0;
  return (
    <AdminShell>
      <section className="admin-head">
        <p className="eyebrow">Editor desk</p>
        <h1>Good morning.</h1>
        <Link className="button" to="/admin/posts/new">
          New article
        </Link>
      </section>
      {docs.loading ? (
        <State loading />
      ) : (
        <>
          <div className="stats">
            <div>
              <b>{docs.data?.count || 0}</b>
              <span>Accessible articles</span>
            </div>
            <div>
              <b>{all.filter((d) => d.is_published).length}</b>
              <span>Published on this page</span>
            </div>
            <div>
              <b>{cats}</b>
              <span>Categories</span>
            </div>
          </div>
          <h2>Recent articles</h2>
          <div className="admin-list">
            {all.map((d) => (
              <Link key={d.id} to={`/admin/posts/${d.id}/edit`}>
                <span>{d.title}</span>
                <small>
                  {d.is_published ? "Published" : "Draft"} ·{" "}
                  {date(d.updated_at)}
                </small>
              </Link>
            ))}
          </div>
        </>
      )}
    </AdminShell>
  );
}
function Posts() {
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [confirming, setConfirming] = useState<Document | undefined>();
  const [error, setError] = useState("");
  const result = useLoad(
    () => api.documents({ page, ordering: "-created_at" }),
    [page, refresh],
  );
  const remove = async () => {
    if (!confirming) return;
    try {
      await api.remove(confirming.id);
      setConfirming(undefined);
      setRefresh((v) => v + 1);
    } catch (e: any) {
      setConfirming(undefined);
      setError(e.message);
    }
  };
  return (
    <AdminShell>
      <section className="admin-head">
        <div>
          <p className="eyebrow">Content</p>
          <h1>Articles</h1>
        </div>
        <Link className="button" to="/admin/posts/new">
          New article
        </Link>
      </section>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {result.loading || result.error ? (
        <State loading={result.loading} error={result.error} />
      ) : (
        <>
          <div className="table">
            {result.data?.results.map((d) => (
              <div key={d.id}>
                <span>
                  <b>{d.title}</b>
                  <small>
                    {d.author} · {d.category?.name || "Uncategorised"}
                  </small>
                </span>
                <span>{d.is_published ? "Published" : "Draft"}</span>
                <span>{date(d.updated_at)}</span>
                <Link to={`/admin/posts/${d.id}/edit`}>Edit</Link>
                <button onClick={() => setConfirming(d)}>Delete</button>
              </div>
            ))}
          </div>
          {result.data && <Pager page={result.data} setPage={setPage} />}
        </>
      )}
      {confirming && (
        <ConfirmDialog
          title="Delete article?"
          detail={`“${confirming.title}” will be permanently deleted.`}
          onCancel={() => setConfirming(undefined)}
          onConfirm={remove}
        />
      )}
    </AdminShell>
  );
}
function Categories() {
  const [refresh, setRefresh] = useState(0);
  const [page, setPage] = useState(1);
  const [form, setForm] = useState({ name: "", slug: "" });
  const [editing, setEditing] = useState<Category | undefined>();
  const [confirming, setConfirming] = useState<Category | undefined>();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const result = useLoad(() => api.categories({ page }), [page, refresh]);
  const list = Array.isArray(result.data)
    ? result.data
    : result.data?.results || [];
  const slugify = (value: string) =>
    value
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");
  const edit = (category: Category) => {
    setEditing(category);
    setForm({ name: category.name, slug: category.slug });
    setError("");
    setMessage("");
  };
  const cancel = () => {
    setEditing(undefined);
    setForm({ name: "", slug: "" });
    setError("");
  };
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = form.name.trim();
    const slug = form.slug.trim();
    if (!name || !slug) return setError("Name and slug are required.");
    setSaving(true);
    setError("");
    try {
      if (editing) await api.updateCategory(editing.id, { name, slug });
      else await api.createCategory({ name, slug });
      setMessage(editing ? "Category updated." : "Category created.");
      cancel();
      setRefresh((v) => v + 1);
    } catch (e: any) {
      setError(e.fields ? Object.values(e.fields).flat().join(" ") : e.message);
    } finally {
      setSaving(false);
    }
  };
  const remove = async () => {
    if (!confirming) return;
    try {
      await api.removeCategory(confirming.id);
      setMessage("Category deleted.");
      setConfirming(undefined);
      setRefresh((v) => v + 1);
    } catch (e: any) {
      setConfirming(undefined);
      setError(e.message);
    }
  };
  return (
    <AdminShell>
      <section className="admin-head">
        <div>
          <p className="eyebrow">Taxonomy</p>
          <h1>Categories</h1>
        </div>
      </section>
      <div className="category-manager">
        <form className="editor" onSubmit={submit}>
          <h2>{editing ? "Edit category" : "New category"}</h2>
          <label>
            Name
            <input
              value={form.name}
              onChange={(e) => {
                const name = e.target.value;
                setForm((current) => ({
                  name,
                  slug: editing ? current.slug : slugify(name),
                }));
              }}
              required
            />
          </label>
          <label>
            Slug
            <input
              value={form.slug}
              onChange={(e) =>
                setForm((current) => ({
                  ...current,
                  slug: slugify(e.target.value),
                }))
              }
              required
            />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          {message && (
            <p className="form-success" role="status">
              {message}
            </p>
          )}
          <div>
            <button disabled={saving}>
              {saving
                ? "Saving…"
                : editing
                  ? "Save category"
                  : "Create category"}
            </button>
            {editing && (
              <button
                type="button"
                className="secondary-button"
                onClick={cancel}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
        <section className="category-list">
          <h2>All categories</h2>
          {result.loading || result.error ? (
            <State loading={result.loading} error={result.error} />
          ) : list.length ? (
            <>
              {list.map((category: Category) => (
                <div key={category.id}>
                  <span>
                    <b>{category.name}</b>
                    <small>/{category.slug}</small>
                  </span>
                  <button
                    className="link-button"
                    onClick={() => edit(category)}
                  >
                    Edit
                  </button>
                  <button
                    className="link-button danger-link"
                    onClick={() => setConfirming(category)}
                  >
                    Delete
                  </button>
                </div>
              ))}
              {result.data && !Array.isArray(result.data) && (
                <Pager page={result.data} setPage={setPage} />
              )}
            </>
          ) : (
            <State empty="No categories yet." />
          )}
        </section>
      </div>
      {confirming && (
        <ConfirmDialog
          title="Delete category?"
          detail={`“${confirming.name}” will be permanently deleted. The server may reject this if documents still use it.`}
          onCancel={() => setConfirming(undefined)}
          onConfirm={remove}
        />
      )}
    </AdminShell>
  );
}
function Editor() {
  const { id } = useParams();
  const nav = useNavigate();
  const existing = useLoad(
    () => (id ? api.document(id) : Promise.resolve(undefined)),
    [id],
  );
  const categories = useLoad(() => api.categories(), []);
  const [form, setForm] = useState({
    title: "",
    author: "",
    content: "",
    category_id: "",
    tags: "",
    is_published: true,
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    const d = existing.data;
    if (d)
      setForm({
        title: d.title,
        author: d.author,
        content: d.content,
        category_id: d.category ? String(d.category.id) : "",
        tags: d.tags.join(", "),
        is_published: d.is_published,
      });
  }, [existing.data]);
  const list = Array.isArray(categories.data)
    ? categories.data
    : categories.data?.results || [];
  const change = (key: string, value: string | boolean) =>
    setForm((prev) => ({ ...prev, [key]: value }));
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !form.title.trim() ||
      !form.author.trim() ||
      !form.content.trim() ||
      !form.category_id
    )
      return setError("Title, author, category, and content are required.");
    setSaving(true);
    setError("");
    const payload = {
      title: form.title.trim(),
      author: form.author.trim(),
      content: form.content.trim(),
      category_id: Number(form.category_id),
      tags: form.tags
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean),
      is_published: form.is_published,
    };
    try {
      id ? await api.update(id, payload) : await api.create(payload);
      nav("/admin/posts");
    } catch (e: any) {
      setError(e.fields ? Object.values(e.fields).flat().join(" ") : e.message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <AdminShell>
      <section className="admin-head">
        <div>
          <p className="eyebrow">{id ? "Edit" : "New"} article</p>
          <h1>{id ? "Refine the draft" : "Start with the idea"}</h1>
        </div>
      </section>
      {existing.loading && id ? (
        <State loading />
      ) : (
        <form className="editor" onSubmit={submit}>
          <label>
            Title
            <input
              value={form.title}
              onChange={(e) => change("title", e.target.value)}
              required
            />
          </label>
          <div className="two">
            <label>
              Author
              <input
                value={form.author}
                onChange={(e) => change("author", e.target.value)}
                required
              />
            </label>
            <label>
              Category
              <select
                value={form.category_id}
                onChange={(e) => change("category_id", e.target.value)}
                required
              >
                <option value="">Choose a category</option>
                {list.map((c: Category) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Tags <small>Separate tags with commas.</small>
            <input
              value={form.tags}
              onChange={(e) => change("tags", e.target.value)}
              placeholder="django, search"
            />
          </label>
          <label>
            Body
            <textarea
              rows={16}
              value={form.content}
              onChange={(e) => change("content", e.target.value)}
              required
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={form.is_published}
              onChange={(e) => change("is_published", e.target.checked)}
            />{" "}
            Publish immediately
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div>
            <button disabled={saving}>
              {saving ? "Saving…" : "Save article"}
            </button>
            <Link className="text-link" to="/admin/posts">
              Cancel
            </Link>
          </div>
        </form>
      )}
    </AdminShell>
  );
}
function NotFound() {
  return (
    <Layout>
      <section className="notfound">
        <p className="eyebrow">404</p>
        <h1>That signal is lost.</h1>
        <p>The page you requested does not exist or is no longer available.</p>
        <Link className="button" to="/">
          Back to home
        </Link>
      </section>
    </Layout>
  );
}
function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/blog" element={<Listing />} />
      <Route path="/blog/:id" element={<Article />} />
      <Route path="/categories/:category" element={<CategoryRoute />} />
      <Route path="/tags/:tag" element={<TagRoute />} />
      <Route path="/search" element={<Search />} />
      <Route path="/admin/login" element={<Login />} />
      <Route
        path="/admin"
        element={
          <Protected>
            <Dashboard />
          </Protected>
        }
      />
      <Route
        path="/admin/posts"
        element={
          <Protected>
            <Posts />
          </Protected>
        }
      />
      <Route
        path="/admin/posts/new"
        element={
          <Protected>
            <Editor />
          </Protected>
        }
      />
      <Route
        path="/admin/posts/:id/edit"
        element={
          <Protected>
            <Editor />
          </Protected>
        }
      />
      <Route
        path="/admin/categories"
        element={
          <Protected>
            <Categories />
          </Protected>
        }
      />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
function CategoryRoute() {
  const { category } = useParams();
  return <Listing category={category} />;
}
function TagRoute() {
  const { tag } = useParams();
  return <Listing tag={tag} />;
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
