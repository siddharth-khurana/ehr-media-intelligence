import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, AlertCircle, ArrowDownToLine, ArrowUpRight, CalendarDays, Check,
  ChevronDown, ChevronLeft, ChevronRight, CircleHelp, ClipboardList, CloudUpload,
  Database, FileCheck2, FileText, Filter, HeartPulse, Layers3, Loader2, Menu,
  Microscope, MoreHorizontal, PanelRightClose, RefreshCw, Search, ShieldCheck,
  Sparkles, Stethoscope, X, Zap
} from "lucide-react";
import { api } from "./api";

const typeLabels = {
  DocumentReference: "Document",
  DiagnosticReport: "Diagnostic report",
  Patient: "Patient"
};

function cx(...values) { return values.filter(Boolean).join(" "); }
function initials(name = "") {
  return name.split(" ").filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "PT";
}
function prettyDate(value) {
  if (!value) return "Date not provided";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function scorePercent(score) {
  const value = Number(score);
  return Number.isFinite(value) ? `${Math.max(0, Math.min(100, Math.round(value * 100)))}%` : "—";
}

function App() {
  const [activeTab, setActiveTab] = useState("search");
  const [patients, setPatients] = useState([]);
  const [query, setQuery] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [health, setHealth] = useState("checking");
  const [error, setError] = useState("");
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientDetail, setPatientDetail] = useState(null);
  const [bundleData, setBundleData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [uploadFiles, setUploadFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [toast, setToast] = useState("");

  const loadPatients = useCallback(async () => {
    try {
      const data = await api.patients();
      setPatients(data.items || []);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    api.health().then(() => setHealth("connected")).catch(() => setHealth("offline"));
    loadPatients();
  }, [loadPatients]);

  const patientMap = useMemo(() => new Map(patients.map((p) => [p.patient_id, p])), [patients]);

  async function handleSearch(event) {
    event?.preventDefault();
    if (!query.trim()) {
      setError("Enter a natural-language search to find patient records.");
      return;
    }
    setLoading(true); setError(""); setSearched(true);
    try {
      const data = await api.search({
        query: query.trim(),
        resource_type: resourceType || null,
        start_date: startDate || null,
        end_date: endDate || null,
        top_k: 5
      });
      setResults(data.results || []);
    } catch (e) {
      setResults([]);
      setError(e.message);
    } finally { setLoading(false); }
  }

  async function openPatient(patientId) {
    setSelectedPatient(patientId);
    setPatientDetail(null); setBundleData(null); setSummary(null);
    setDetailLoading(true);
    try {
      const [detail, bundle] = await Promise.all([
        api.patient(patientId),
        api.bundle(patientId).catch(() => null)
      ]);
      setPatientDetail(detail);
      setBundleData(bundle);
    } catch (e) { setError(e.message); }
    finally { setDetailLoading(false); }
  }

  async function generateSummary() {
    if (!selectedPatient) return;
    setSummaryLoading(true); setError("");
    try { setSummary(await api.summary(selectedPatient)); }
    catch (e) { setError(e.message); }
    finally { setSummaryLoading(false); }
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!uploadFiles.length) return;
    setUploading(true); setError(""); setUploadResult(null);
    try {
      const result = await api.ingest(uploadFiles);
      setUploadResult(result);
      setUploadFiles([]);
      await loadPatients();
      setToast("Records ingested successfully");
      window.setTimeout(() => setToast(""), 3200);
    } catch (e) { setError(e.message); }
    finally { setUploading(false); }
  }

  async function handleIndex() {
    setIndexing(true); setError("");
    try {
      const result = await api.index();
      setToast(`Indexed ${result.indexed || 0} records`);
      window.setTimeout(() => setToast(""), 3200);
    } catch (e) { setError(e.message); }
    finally { setIndexing(false); }
  }

  function clearFilters() {
    setResourceType(""); setStartDate(""); setEndDate("");
  }

  const navItems = [
    { id: "search", label: "Media search", icon: Search },
    { id: "patients", label: "Patients", icon: HeartPulse },
    { id: "ingest", label: "Data ingestion", icon: CloudUpload }
  ];

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-800">
      <div className="flex min-h-screen">
        <aside className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-[258px] flex-col border-r border-slate-200/80 bg-white px-5 py-6 transition-transform lg:static lg:translate-x-0",
          mobileNavOpen ? "translate-x-0" : "-translate-x-full"
        )}>
          <div className="flex items-center gap-3 px-1">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-600 text-white shadow-sm">
              <Activity size={21} strokeWidth={2.5} />
            </div>
            <div>
              <div className="text-[15px] font-bold tracking-tight text-slate-900">onye<span className="text-teal-600">.</span></div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Media intelligence</div>
            </div>
            <button className="ml-auto rounded-lg p-2 text-slate-400 hover:bg-slate-100 lg:hidden" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation"><X size={18}/></button>
          </div>

          <div className="mt-10">
            <p className="px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Workspace</p>
            <nav className="mt-3 space-y-1" aria-label="Main navigation">
              {navItems.map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => { setActiveTab(id); setMobileNavOpen(false); }}
                  className={cx("nav-item", activeTab === id && "nav-item-active")}>
                  <Icon size={18}/><span>{label}</span>
                  {id === "search" && <span className="ml-auto rounded-md bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-teal-700">AI</span>}
                </button>
              ))}
            </nav>
          </div>

          <div className="mt-9">
            <p className="px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Platform</p>
            <div className="mt-3 space-y-1">
              <div className="nav-item cursor-default"><Layers3 size={18}/><span>FHIR R4 resources</span></div>
              <div className="nav-item cursor-default"><Database size={18}/><span>Local data store</span></div>
              <div className="nav-item cursor-default"><ShieldCheck size={18}/><span>Audit & validation</span></div>
            </div>
          </div>

          <div className="mt-auto rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50 to-cyan-50 p-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-teal-700 shadow-sm"><Sparkles size={16}/></div>
            <p className="mt-3 text-sm font-semibold text-slate-800">Clinical intelligence</p>
            <p className="mt-1 text-xs leading-5 text-slate-500">Search across unstructured media and surface relevant records faster.</p>
            <div className="mt-3 flex items-center gap-1.5 text-[10px] font-semibold text-teal-700"><span className="h-1.5 w-1.5 rounded-full bg-teal-500"/> Synthetic demo workspace</div>
          </div>
          <div className="mt-5 flex items-center gap-2 px-1 text-[11px] text-slate-400">
            <span className={cx("h-2 w-2 rounded-full", health === "connected" ? "bg-emerald-500" : health === "offline" ? "bg-rose-500" : "bg-amber-400")}/>
            API {health === "connected" ? "connected" : health === "offline" ? "unavailable" : "checking"}
          </div>
        </aside>

        {mobileNavOpen && <button className="fixed inset-0 z-30 bg-slate-900/30 lg:hidden" onClick={() => setMobileNavOpen(false)} aria-label="Close menu overlay"/>}

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur md:px-8">
            <div className="flex items-center gap-3">
              <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation"><Menu size={20}/></button>
              <div>
                <div className="text-sm font-semibold text-slate-900">EHR Media Intelligence</div>
                <div className="hidden text-[11px] text-slate-400 sm:block">Clinical records workspace / {navItems.find((n) => n.id === activeTab)?.label}</div>
              </div>
            </div>
            <div className="flex items-center gap-2 md:gap-4">
              <div className="hidden items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 sm:flex">
                <span className={cx("h-2 w-2 rounded-full", health === "connected" ? "bg-emerald-500" : "bg-rose-500")}/>
                <span className="text-[11px] font-medium text-slate-500">{health === "connected" ? "System operational" : "API disconnected"}</span>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">CL</div>
            </div>
          </header>

          <div className="mx-auto max-w-[1440px] px-4 py-7 md:px-8 md:py-9">
            {error && <div role="alert" className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"><AlertCircle size={18} className="mt-0.5 shrink-0"/><span className="flex-1">{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X size={16}/></button></div>}

            {activeTab === "search" && (
              <SearchPage
                query={query} setQuery={setQuery} resourceType={resourceType} setResourceType={setResourceType}
                startDate={startDate} setStartDate={setStartDate} endDate={endDate} setEndDate={setEndDate}
                onSearch={handleSearch} loading={loading} searched={searched} results={results}
                patientMap={patientMap} onOpenPatient={openPatient} onIndex={handleIndex} indexing={indexing}
                onClear={clearFilters}
              />
            )}
            {activeTab === "patients" && <PatientsPage patients={patients} onRefresh={loadPatients} onOpenPatient={openPatient}/>}
            {activeTab === "ingest" && (
              <IngestPage files={uploadFiles} setFiles={setUploadFiles} onSubmit={handleUpload}
                uploading={uploading} result={uploadResult} onIndex={handleIndex} indexing={indexing}/>
            )}
          </div>
        </main>
      </div>

      {selectedPatient && (
        <PatientDrawer patientId={selectedPatient} patient={patientDetail?.patient} records={patientDetail?.records || []}
          bundleData={bundleData} summary={summary} detailLoading={detailLoading} summaryLoading={summaryLoading}
          onClose={() => setSelectedPatient(null)} onSummary={generateSummary}/>
      )}
      {toast && <div role="status" className="fixed bottom-5 right-5 z-[70] flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white shadow-xl"><Check size={17} className="text-emerald-400"/>{toast}</div>}
    </div>
  );
}

function PageHeading({ eyebrow, title, description, action }) {
  return <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
    <div><p className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-teal-700">{eyebrow}</p>
      <h1 className="text-[26px] font-bold tracking-tight text-slate-900 md:text-[30px]">{title}</h1>
      <p className="mt-1.5 max-w-2xl text-sm leading-6 text-slate-500">{description}</p></div>
    {action}
  </div>;
}

function SearchPage({ query, setQuery, resourceType, setResourceType, startDate, setStartDate, endDate, setEndDate, onSearch, loading, searched, results, patientMap, onOpenPatient, onIndex, indexing, onClear }) {
  return <>
    <PageHeading eyebrow="AI-powered discovery" title="Find the right record, faster."
      description="Search patient media, reports and clinical notes using natural language. Results are ranked by semantic relevance."
      action={<button className="btn-secondary" onClick={onIndex} disabled={indexing}><RefreshCw size={15} className={indexing ? "animate-spin" : ""}/>{indexing ? "Indexing…" : "Refresh search index"}</button>}/>
    <form onSubmit={onSearch} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel md:p-5">
      <label htmlFor="clinical-search" className="mb-2 block text-xs font-semibold text-slate-700">What are you looking for?</label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative min-w-0 flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={19}/>
          <input id="clinical-search" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. patient with recent imaging and abnormal lab results"
            className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/10"/>
        </div>
        <button className="btn-primary h-12 justify-center sm:min-w-[132px]" type="submit" disabled={loading}>
          {loading ? <Loader2 size={17} className="animate-spin"/> : <Search size={17}/>}
          {loading ? "Searching…" : "Search records"}
        </button>
      </div>
      <div className="mt-4 flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-end">
        <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-3">
          <label className="field-label">Resource type
            <select value={resourceType} onChange={(e) => setResourceType(e.target.value)} className="field-control">
              <option value="">All resource types</option><option value="DocumentReference">Document</option><option value="DiagnosticReport">Diagnostic report</option>
            </select>
          </label>
          <label className="field-label">From date<input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="field-control"/></label>
          <label className="field-label">To date<input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="field-control"/></label>
        </div>
        <button type="button" onClick={onClear} className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg px-3 text-xs font-semibold text-slate-500 hover:bg-slate-100"><Filter size={14}/> Clear filters</button>
      </div>
    </form>

    <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-base font-bold text-slate-900">{searched ? "Search results" : "Explore your workspace"}</h2>
        <p className="mt-1 text-xs text-slate-400">{searched ? `${results.length} matching records · top 5 ranked results` : "Start with a natural-language question or browse recent patient records."}</p></div>
      {searched && <span className="rounded-full bg-teal-50 px-3 py-1 text-[11px] font-semibold text-teal-700">Semantic search</span>}
    </div>

    {!searched ? <div className="mt-4 grid gap-4 md:grid-cols-3">
      <SuggestionCard icon={Microscope} title="Imaging & radiology" prompt="Find recent imaging reports and radiology notes" setQuery={setQuery}/>
      <SuggestionCard icon={Activity} title="Lab results" prompt="Show records mentioning abnormal laboratory results" setQuery={setQuery}/>
      <SuggestionCard icon={ClipboardList} title="Discharge notes" prompt="Find discharge summaries and follow-up instructions" setQuery={setQuery}/>
    </div> : loading ? <div className="mt-4 rounded-2xl border border-slate-200 bg-white py-16 text-center"><Loader2 className="mx-auto animate-spin text-teal-600" size={26}/><p className="mt-3 text-sm font-medium text-slate-600">Searching clinical records…</p></div>
      : results.length ? <div className="mt-4 space-y-3">{results.map((result, index) => <ResultCard key={result.record_id} result={result} index={index} patient={patientMap.get(result.patient_id)} onOpen={() => onOpenPatient(result.patient_id)}/>)}</div>
      : <EmptyState icon={Search} title="No matching records found" description="Try a broader search, remove a filter, or check that records have been ingested and indexed."/>}
    <div className="mt-7 flex items-start gap-2 rounded-xl border border-amber-100 bg-amber-50/70 p-3.5 text-[11px] leading-5 text-amber-800"><ShieldCheck size={16} className="mt-0.5 shrink-0"/><p><strong>Clinical safety:</strong> Search relevance and AI summaries are for information retrieval only. Always review the original source record. This demo uses synthetic data and is not intended for clinical decision-making.</p></div>
  </>;
}

function SuggestionCard({ icon: Icon, title, prompt, setQuery }) {
  return <button onClick={() => setQuery(prompt)} className="group rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-panel transition hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-soft">
    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-50 text-teal-700"><Icon size={18}/></div>
    <div className="mt-4 flex items-center justify-between"><span className="text-sm font-semibold text-slate-800">{title}</span><ArrowUpRight size={16} className="text-slate-300 transition group-hover:text-teal-600"/></div>
    <p className="mt-1 text-xs leading-5 text-slate-500">{prompt}</p>
  </button>;
}

function ResultCard({ result, index, patient, onOpen }) {
  const name = patient?.full_name || result.patient_id;
  return <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel transition hover:border-slate-300 md:p-5">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-600">{initials(name)}</div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-bold text-slate-900">{result.text?.split("\n")[0]?.slice(0, 90) || "Clinical record"}</h3>
          <span className={cx("rounded-md px-2 py-1 text-[10px] font-semibold", result.resource_type === "DiagnosticReport" ? "bg-violet-50 text-violet-700" : "bg-sky-50 text-sky-700")}>{typeLabels[result.resource_type] || result.resource_type}</span>
        </div>
        <button onClick={onOpen} className="mt-1 text-xs font-semibold text-teal-700 hover:text-teal-800">{name} <span className="font-normal text-slate-400">· {patient?.mrn || "MRN not available"}</span></button>
        <p className="mt-3 line-clamp-2 text-xs leading-5 text-slate-500">{result.text?.split("\n").slice(1).join(" ") || result.text}</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[10px] text-slate-400">
          <span className="inline-flex items-center gap-1"><CalendarDays size={13}/>{prettyDate(result.record_date)}</span>
          <span className="inline-flex items-center gap-1"><FileText size={13}/>ID: {result.record_id}</span>
        </div>
      </div>
      <div className="flex items-center justify-between gap-4 sm:flex-col sm:items-end">
        <div className="text-right"><div className="text-lg font-bold tabular-nums text-teal-700">{scorePercent(result.relevance_score)}</div><div className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">Relevance</div></div>
        <button onClick={onOpen} className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-teal-700">View patient <ChevronRight size={14}/></button>
      </div>
    </div>
  </article>;
}

function PatientsPage({ patients, onRefresh, onOpenPatient }) {
  const [filter, setFilter] = useState("");
  const filtered = patients.filter((p) => `${p.full_name} ${p.mrn} ${p.patient_id}`.toLowerCase().includes(filter.toLowerCase()));
  return <>
    <PageHeading eyebrow="Patient directory" title="Patients" description="Browse synthetic patient profiles and open their linked clinical records."
      action={<button onClick={onRefresh} className="btn-secondary"><RefreshCw size={15}/> Refresh list</button>}/>
    <div className="mb-4 flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
      <div><div className="text-2xl font-bold text-slate-900">{patients.length}</div><div className="text-xs text-slate-400">Patients in workspace</div></div>
      <div className="relative w-full sm:max-w-xs"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"/><input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search name, MRN or ID" className="field-control pl-9"/></div>
    </div>
    {filtered.length ? <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
      <div className="hidden grid-cols-[minmax(200px,1.5fr)_1fr_1fr_120px] gap-4 border-b border-slate-100 bg-slate-50/80 px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 md:grid"><span>Patient</span><span>Patient ID</span><span>Date of birth</span><span>Gender</span></div>
      {filtered.map((p) => <button key={p.patient_id} onClick={() => onOpenPatient(p.patient_id)} className="grid w-full grid-cols-1 gap-2 border-b border-slate-100 px-4 py-4 text-left transition last:border-0 hover:bg-slate-50 md:grid-cols-[minmax(200px,1.5fr)_1fr_1fr_120px] md:items-center md:gap-4 md:px-5">
        <span className="flex min-w-0 items-center gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-[11px] font-bold text-teal-700">{initials(p.full_name)}</span><span className="min-w-0"><span className="block truncate text-sm font-semibold text-slate-800">{p.full_name}</span><span className="block text-[11px] text-slate-400">{p.mrn || "No MRN"}</span></span></span>
        <span className="text-xs text-slate-500 md:pl-0"><span className="mr-2 text-[10px] text-slate-400 md:hidden">ID</span>{p.patient_id}</span>
        <span className="text-xs text-slate-500"><span className="mr-2 text-[10px] text-slate-400 md:hidden">DOB</span>{prettyDate(p.dob)}</span>
        <span className="text-xs capitalize text-slate-500"><span className="mr-2 text-[10px] text-slate-400 md:hidden">Gender</span>{p.gender || "Unknown"}</span>
      </button>)}
    </div> : <EmptyState icon={HeartPulse} title="No patients found" description="Ingest a synthetic JSON, CSV or TXT file to populate the patient directory."/>}
  </>;
}

function IngestPage({ files, setFiles, onSubmit, uploading, result, onIndex, indexing }) {
  const [dragging, setDragging] = useState(false);
  function addFiles(list) {
    const allowed = Array.from(list || []).filter((file) => /\.(json|csv|txt)$/i.test(file.name));
    setFiles((current) => [...current, ...allowed].filter((file, i, arr) => arr.findIndex((f) => f.name === file.name && f.size === file.size) === i));
  }
  return <>
    <PageHeading eyebrow="Data pipeline" title="Ingest patient media" description="Upload simulated EHR exports to clean records, normalize them to FHIR R4 and prepare them for semantic discovery."/>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel md:p-6">
        <div className="flex items-center gap-2"><CloudUpload size={19} className="text-teal-700"/><h2 className="text-sm font-bold text-slate-900">Upload source files</h2></div>
        <p className="mt-1 text-xs leading-5 text-slate-500">Supported formats: JSON, CSV and plain text (TXT). Upload synthetic data only.</p>
        <form onSubmit={onSubmit}>
          <label onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
            className={cx("mt-5 flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-5 py-8 text-center transition", dragging ? "border-teal-500 bg-teal-50" : "border-slate-200 bg-slate-50/70 hover:border-teal-300 hover:bg-teal-50/40")}>
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-teal-700 shadow-sm"><CloudUpload size={23}/></span>
            <span className="mt-4 text-sm font-semibold text-slate-800">Drop files here or <span className="text-teal-700">browse</span></span>
            <span className="mt-1 text-xs text-slate-400">JSON, CSV or TXT · Max 10 MB per file</span>
            <input type="file" multiple accept=".json,.csv,.txt,application/json,text/csv,text/plain" className="sr-only" onChange={(e) => addFiles(e.target.files)} aria-label="Choose files to upload"/>
          </label>
          {files.length > 0 && <div className="mt-4 space-y-2">{files.map((file, i) => <div key={`${file.name}-${i}`} className="flex items-center gap-3 rounded-xl border border-slate-100 px-3 py-2.5"><FileText size={17} className="text-slate-400"/><span className="min-w-0 flex-1 truncate text-xs font-medium text-slate-700">{file.name}</span><span className="text-[10px] text-slate-400">{(file.size / 1024).toFixed(1)} KB</span><button type="button" onClick={() => setFiles((current) => current.filter((_, j) => j !== i))} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-rose-600" aria-label={`Remove ${file.name}`}><X size={15}/></button></div>)}</div>}
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><button type="button" className="btn-secondary justify-center" onClick={() => setFiles([])} disabled={!files.length}>Clear selection</button><button className="btn-primary justify-center" type="submit" disabled={!files.length || uploading}>{uploading ? <Loader2 size={16} className="animate-spin"/> : <CloudUpload size={16}/>} {uploading ? "Processing files…" : "Ingest records"}</button></div>
        </form>
        {result && <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-center gap-2 text-sm font-bold text-emerald-800"><Check size={17}/> Ingestion completed</div>
          <div className="mt-3 grid grid-cols-3 gap-2">{[["Files",result.files_processed],["Patients",result.patients_processed],["Records",result.records_processed]].map(([label,value]) => <div key={label} className="rounded-lg bg-white/80 p-3"><div className="text-xl font-bold text-slate-900">{value}</div><div className="text-[10px] text-slate-500">{label}</div></div>)}</div>
          {result.errors?.length > 0 && <div className="mt-3 text-xs text-rose-700">{result.errors.join(" · ")}</div>}
          {result.audit_logs?.length > 0 && <details className="mt-3 text-xs text-emerald-800"><summary className="cursor-pointer font-semibold">View data cleaning audit log ({result.audit_logs.length})</summary><pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-white p-3 text-[10px]">{JSON.stringify(result.audit_logs,null,2)}</pre></details>}
          <button className="btn-primary mt-4" onClick={onIndex} disabled={indexing}>{indexing ? <Loader2 size={15} className="animate-spin"/> : <Zap size={15}/>} {indexing ? "Indexing…" : "Build semantic search index"}</button>
        </div>}
      </section>
      <aside className="space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel">
          <h3 className="text-sm font-bold text-slate-900">Processing pipeline</h3>
          <div className="mt-5 space-y-4">
            {[
              ["01","Data ingestion","Read source files and parse records",CloudUpload],
              ["02","Data cleaning","Normalize demographics and audit changes",RefreshCw],
              ["03","FHIR R4 mapping","Create Patient and clinical resources",FileCheck2],
              ["04","Ready for discovery","Index records for semantic search",Search]
            ].map(([number,title,desc,Icon],i) => <div key={number} className="flex gap-3"><div className="flex flex-col items-center"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-50 text-teal-700"><Icon size={15}/></span>{i !== 3 && <span className="mt-1 h-6 w-px bg-slate-200"/>}</div><div className="pb-1"><div className="text-[10px] font-bold text-slate-400">{number}</div><div className="text-xs font-semibold text-slate-800">{title}</div><div className="mt-0.5 text-[11px] leading-4 text-slate-400">{desc}</div></div></div>)}
          </div>
        </div>
        <div className="rounded-2xl border border-amber-100 bg-amber-50/70 p-4"><div className="flex gap-2 text-amber-800"><ShieldCheck size={17}/><span className="text-xs font-bold">Data handling reminder</span></div><p className="mt-2 text-[11px] leading-5 text-amber-800/80">Only upload synthetic or properly de-identified assessment data. Do not upload real patient records or protected health information.</p></div>
      </aside>
    </div>
  </>;
}

function PatientDrawer({ patientId, patient, records, bundleData, summary, detailLoading, summaryLoading, onClose, onSummary }) {
  const [tab, setTab] = useState("overview");
  const [validation, setValidation] = useState(null);
  useEffect(() => { api.validation(patientId).then(setValidation).catch(() => setValidation(null)); }, [patientId]);
  return <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/35 backdrop-blur-[2px]" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
    <section role="dialog" aria-modal="true" aria-labelledby="drawer-title" className="flex h-full w-full max-w-[620px] flex-col overflow-hidden bg-white shadow-2xl">
      <div className="flex items-start justify-between border-b border-slate-200 px-5 py-5 md:px-7">
        <div className="flex min-w-0 gap-3"><div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-sm font-bold text-teal-700">{initials(patient?.full_name)}</div><div className="min-w-0"><h2 id="drawer-title" className="truncate text-base font-bold text-slate-900">{patient?.full_name || "Patient details"}</h2><p className="mt-1 truncate text-xs text-slate-400">{patient?.mrn || "MRN unavailable"} · {patientId}</p></div></div>
        <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Close patient details"><X size={19}/></button>
      </div>
      <div className="flex gap-1 border-b border-slate-100 px-5 md:px-7">
        {["overview","FHIR resources"].map((t) => <button key={t} onClick={() => setTab(t)} className={cx("border-b-2 px-3 py-3 text-xs font-semibold capitalize",tab === t ? "border-teal-600 text-teal-700" : "border-transparent text-slate-400 hover:text-slate-700")}>{t}</button>)}
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-5 md:px-7">
        {detailLoading ? <div className="py-16 text-center"><Loader2 className="mx-auto animate-spin text-teal-600" size={24}/><p className="mt-3 text-xs text-slate-400">Loading patient record…</p></div> :
        tab === "overview" ? <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <InfoTile label="Date of birth" value={prettyDate(patient?.dob)}/><InfoTile label="Gender" value={patient?.gender || "Unknown"}/><InfoTile label="Linked records" value={records.length}/>
          </div>
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3"><div><h3 className="text-sm font-bold text-slate-900">AI clinical summary</h3><p className="mt-1 text-[11px] text-slate-400">Generated from available patient records</p></div><button className="btn-primary" onClick={onSummary} disabled={summaryLoading || !records.length}>{summaryLoading ? <Loader2 size={15} className="animate-spin"/> : <Sparkles size={15}/>} {summary ? "Refresh summary" : "Generate summary"}</button></div>
          {summary ? <div className="mt-3 rounded-xl border border-teal-100 bg-teal-50/50 p-4">
            <SummarySection title="Chief concern" items={summary.chief_concern ? [summary.chief_concern] : []}/>
            <SummarySection title="Key diagnoses" items={summary.key_diagnoses}/>
            <SummarySection title="Recent media records" items={summary.recent_media_records}/>
            <SummarySection title="Flagged anomalies" items={summary.flagged_anomalies}/>
            <div className="mt-4 border-t border-teal-100 pt-3 text-[10px] leading-4 text-slate-500"><strong>Confidence:</strong> {summary.confidence}<br/>{summary.disclaimer}<br/>{summary.cached ? "Served from cache." : "Newly generated."}</div>
          </div> : <div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-5 text-center"><Sparkles size={20} className="mx-auto text-slate-300"/><p className="mt-2 text-xs font-semibold text-slate-600">No summary generated yet</p><p className="mt-1 text-[11px] text-slate-400">Generate a structured summary from this patient's record history.</p></div>}
          <div className="mt-7"><div className="mb-3 flex items-center justify-between"><h3 className="text-sm font-bold text-slate-900">Clinical media records</h3><span className="text-[10px] text-slate-400">{records.length} records</span></div>
            {records.length ? <div className="space-y-2">{records.map((record) => <div key={record.record_id} className="rounded-xl border border-slate-200 p-3"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="truncate text-xs font-semibold text-slate-800">{record.title || "Clinical record"}</div><div className="mt-1 text-[10px] text-slate-400">{prettyDate(record.record_date)} · {record.record_id}</div></div><span className="shrink-0 rounded-md bg-slate-100 px-2 py-1 text-[9px] font-semibold text-slate-600">{typeLabels[record.resource_type] || record.resource_type}</span></div><p className="mt-2 line-clamp-3 text-[11px] leading-5 text-slate-500">{record.text_content || "No text content."}</p></div>)}</div> : <EmptyState icon={FileText} title="No linked records" description="No records were returned for this patient."/ >}
          </div>
        </> : <>
          <div className="flex items-center justify-between"><div><h3 className="text-sm font-bold text-slate-900">FHIR R4 Bundle</h3><p className="mt-1 text-[11px] text-slate-400">Normalized resources and validation status</p></div><span className={cx("rounded-full px-2.5 py-1 text-[10px] font-semibold", validation?.valid ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700")}>{validation?.valid ? "Valid model" : "Not validated"}</span></div>
          {bundleData?.bundle ? <><div className="mt-4 grid grid-cols-2 gap-3"><InfoTile label="Bundle type" value={bundleData.bundle.type}/><InfoTile label="Resources" value={bundleData.bundle.entry?.length || 0}/></div><div className="mt-4 space-y-2">{(bundleData.bundle.entry || []).map((entry,i) => <div key={i} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-50 text-teal-700"><FileCheck2 size={15}/></span><div><div className="text-xs font-semibold text-slate-800">{entry.resource?.resourceType}</div><div className="text-[10px] text-slate-400">{entry.resource?.id}</div></div></div>)}</div><details className="mt-4"><summary className="cursor-pointer text-xs font-semibold text-teal-700">View raw Bundle JSON</summary><pre className="mt-2 max-h-72 overflow-auto rounded-xl bg-slate-950 p-3 text-[10px] leading-5 text-emerald-100">{JSON.stringify(bundleData.bundle,null,2)}</pre></details></> : <EmptyState icon={FileCheck2} title="FHIR Bundle unavailable" description="The backend has not returned a Bundle for this patient."/>}
          {validation?.errors?.length > 0 && <div className="mt-4 rounded-xl bg-rose-50 p-3 text-xs text-rose-700">{validation.errors.join("\n")}</div>}
        </>}
      </div>
      <div className="border-t border-slate-200 px-5 py-3 text-[10px] leading-4 text-slate-400 md:px-7">AI-generated content is not a clinical decision. Review source records and validate data independently.</div>
    </section>
  </div>;
}

function SummarySection({ title, items }) {
  return <div className="mb-3 last:mb-0"><div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-teal-800">{title}</div>{items?.length ? <ul className="space-y-1">{items.map((item,i) => <li key={i} className="text-xs leading-5 text-slate-700">{typeof item === "string" ? item : JSON.stringify(item)}</li>)}</ul> : <p className="text-[11px] italic text-slate-400">Not documented</p>}</div>;
}
function InfoTile({ label, value }) {
  return <div className="rounded-xl border border-slate-100 bg-slate-50 p-3"><div className="text-[10px] text-slate-400">{label}</div><div className="mt-1 truncate text-sm font-bold capitalize text-slate-800">{value ?? "—"}</div></div>;
}
function EmptyState({ icon: Icon, title, description }) {
  return <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-5 py-12 text-center"><span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-400"><Icon size={20}/></span><h3 className="mt-3 text-sm font-semibold text-slate-700">{title}</h3><p className="mx-auto mt-1 max-w-sm text-xs leading-5 text-slate-400">{description}</p></div>;
}

export default App;
