import { useState, useEffect } from 'react';
import { enrichmentApi, EnrichmentCandidate } from '@/api/enrichment';
import { AlertTriangle, Check, RefreshCw, Edit3, X, ArrowRight, Shield } from 'lucide-react';
import toast from 'react-hot-toast';

interface MetadataState {
  source_title?: string | null;
  source_author?: string | null;
  source_description?: string | null;
  source_publisher?: string | null;
  source_language?: string | null;
  source_isbn?: string | null;
  source_publish_date?: string | null;
  calibrated_title?: string | null;
  calibrated_author?: string | null;
  calibrated_description?: string | null;
  calibrated_publisher?: string | null;
  calibrated_language?: string | null;
  calibrated_isbn?: string | null;
  last_calibrated_at?: string | null;
  metadata_source?: string | null;
}

interface Props {
  bookId: string;
  onMetadataUpdated?: () => void;
}

interface FieldDiff {
  field: string;
  label: string;
  currentValue: string | null;
  incomingValue: string | null;
  willApply: boolean;
}

export function EnrichmentPanel({ bookId, onMetadataUpdated }: Props) {
  const [metadata, setMetadata] = useState<MetadataState | null>(null);
  const [candidates, setCandidates] = useState<{ google_books: EnrichmentCandidate[]; comicvine: EnrichmentCandidate[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<{ provider: string; candidate: EnrichmentCandidate } | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState({
    calibrated_title: '',
    calibrated_author: '',
    calibrated_description: '',
    calibrated_publisher: '',
    calibrated_language: '',
    calibrated_isbn: '',
  });

  useEffect(() => {
    loadMetadata();
  }, [bookId]);

  const loadMetadata = async () => {
    try {
      const { data } = await enrichmentApi.getMetadata(bookId);
      setMetadata(data);
      setEditForm({
        calibrated_title: data.calibrated_title || '',
        calibrated_author: data.calibrated_author || '',
        calibrated_description: data.calibrated_description || '',
        calibrated_publisher: data.calibrated_publisher || '',
        calibrated_language: data.calibrated_language || '',
        calibrated_isbn: data.calibrated_isbn || '',
      });
    } catch {
      setMetadata(null);
    }
  };

  const fetchCandidates = async () => {
    setLoading(true);
    try {
      const { data } = await enrichmentApi.getCandidates(bookId);
      setCandidates(data);
    } catch {
      toast.error('Failed to fetch enrichment candidates');
    }
    setLoading(false);
  };

  const handleSelectCandidate = (provider: string, candidate: EnrichmentCandidate) => {
    setSelectedCandidate({ provider, candidate });
  };

  const buildFieldDiffs = (candidate: EnrichmentCandidate): FieldDiff[] => {
    const diffs: FieldDiff[] = [];
    const m = metadata;

    const addDiff = (field: string, label: string, current: string | null | undefined, incoming: string | null | undefined) => {
      if (!incoming) return;
      diffs.push({
        field,
        label,
        currentValue: current || null,
        incomingValue: incoming,
        willApply: !current,
      });
    };

    addDiff('title', 'Title', m?.source_title, candidate.title);
    addDiff('author', 'Author', m?.source_author, candidate.authors?.join(', '));
    addDiff('description', 'Description', m?.source_description, candidate.description?.slice(0, 150));
    addDiff('publisher', 'Publisher', m?.source_publisher, candidate.publisher);
    addDiff('language', 'Language', m?.source_language, candidate.language);
    addDiff('isbn', 'ISBN', m?.source_isbn, candidate.isbn_13 || candidate.isbn_10);
    addDiff('publish_date', 'Publish Date', m?.source_publish_date, candidate.published_date);

    return diffs;
  };

  const getConflictCount = (candidate: EnrichmentCandidate): number => {
    return buildFieldDiffs(candidate).filter(d => !d.willApply && d.incomingValue).length;
  };

  const applyCandidate = async () => {
    if (!selectedCandidate) return;
    setApplying(true);
    try {
      await enrichmentApi.apply(bookId, selectedCandidate.provider, selectedCandidate.candidate);
      toast.success('Enrichment applied successfully');
      setSelectedCandidate(null);
      setCandidates(null);
      await loadMetadata();
      onMetadataUpdated?.();
    } catch {
      toast.error('Failed to apply enrichment');
    }
    setApplying(false);
  };

  const handleSaveCalibration = async () => {
    const updates: Record<string, string> = {};
    for (const [key, val] of Object.entries(editForm)) {
      if (val.trim()) updates[key] = val.trim();
    }
    if (Object.keys(updates).length === 0) {
      toast.error('No changes to save');
      return;
    }
    try {
      await enrichmentApi.calibrate(bookId, updates);
      toast.success('Metadata calibrated (audited)');
      setEditMode(false);
      await loadMetadata();
      onMetadataUpdated?.();
    } catch {
      toast.error('Failed to save calibration');
    }
  };

  return (
    <div className="border-t pt-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Metadata Management</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setEditMode(!editMode)}
            className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 flex items-center gap-1.5"
          >
            <Edit3 size={14} /> {editMode ? 'Cancel Edit' : 'Manual Edit'}
          </button>
          <button
            onClick={fetchCandidates}
            disabled={loading}
            className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-1.5"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Enrich
          </button>
        </div>
      </div>

      {/* Current metadata summary */}
      {metadata && (
        <div className="text-xs text-gray-500 space-y-1 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <p><span className="font-medium">Source:</span> {metadata.metadata_source || 'N/A'}</p>
          {metadata.source_title && <p><span className="font-medium">Title:</span> {metadata.source_title}</p>}
          {metadata.source_author && <p><span className="font-medium">Author:</span> {metadata.source_author}</p>}
          {metadata.source_publisher && <p><span className="font-medium">Publisher:</span> {metadata.source_publisher}</p>}
          {metadata.source_language && <p><span className="font-medium">Language:</span> {metadata.source_language}</p>}
          {metadata.source_isbn && <p><span className="font-medium">ISBN:</span> {metadata.source_isbn}</p>}
          {metadata.last_calibrated_at && (
            <p><span className="font-medium">Last calibrated:</span> {new Date(metadata.last_calibrated_at).toLocaleString()}</p>
          )}
        </div>
      )}

      {/* Manual edit form */}
      {editMode && (
        <div className="border rounded-lg p-4 space-y-3 bg-white dark:bg-gray-900">
          <h3 className="font-medium text-sm">Calibrate Metadata (Manual Edit)</h3>
          <p className="text-xs text-gray-500">Changes are audited with field-level tracking.</p>
          {Object.entries(editForm).map(([key, val]) => (
            <div key={key} className="flex items-center gap-2">
              <label className="w-28 text-xs font-medium text-gray-600 shrink-0 capitalize">
                {key.replace('calibrated_', '').replace('_', ' ')}
              </label>
              {key === 'calibrated_description' ? (
                <textarea
                  value={val}
                  onChange={(e) => setEditForm({ ...editForm, [key]: e.target.value })}
                  className="flex-1 px-2 py-1 border rounded text-sm resize-none h-16"
                />
              ) : (
                <input
                  value={val}
                  onChange={(e) => setEditForm({ ...editForm, [key]: e.target.value })}
                  className="flex-1 px-2 py-1 border rounded text-sm"
                />
              )}
            </div>
          ))}
          <button
            onClick={handleSaveCalibration}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            Save Calibration
          </button>
        </div>
      )}

      {/* Enrichment candidates */}
      {candidates && (
        <div className="space-y-4">
          {candidates.google_books.length > 0 && (
            <CandidateList
              title="Google Books"
              items={candidates.google_books}
              selected={selectedCandidate?.provider === 'google_books' ? selectedCandidate.candidate : null}
              onSelect={(c) => handleSelectCandidate('google_books', c)}
              getConflictCount={getConflictCount}
            />
          )}
          {candidates.comicvine.length > 0 && (
            <CandidateList
              title="ComicVine"
              items={candidates.comicvine}
              selected={selectedCandidate?.provider === 'comicvine' ? selectedCandidate.candidate : null}
              onSelect={(c) => handleSelectCandidate('comicvine', c)}
              getConflictCount={getConflictCount}
            />
          )}
          {candidates.google_books.length === 0 && candidates.comicvine.length === 0 && (
            <p className="text-sm text-gray-500">No enrichment candidates found.</p>
          )}
        </div>
      )}

      {/* Confirmation dialog with field-level diff */}
      {selectedCandidate && (
        <FieldDiffConfirm
          provider={selectedCandidate.provider}
          candidate={selectedCandidate.candidate}
          diffs={buildFieldDiffs(selectedCandidate.candidate)}
          applying={applying}
          onConfirm={applyCandidate}
          onCancel={() => setSelectedCandidate(null)}
        />
      )}
    </div>
  );
}

function CandidateList({
  title,
  items,
  selected,
  onSelect,
  getConflictCount,
}: {
  title: string;
  items: EnrichmentCandidate[];
  selected: EnrichmentCandidate | null;
  onSelect: (c: EnrichmentCandidate) => void;
  getConflictCount: (c: EnrichmentCandidate) => number;
}) {
  return (
    <div>
      <h3 className="text-sm font-medium mb-2">{title} Results</h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {items.map((item, idx) => {
          const conflicts = getConflictCount(item);
          const isSelected = selected === item;
          return (
            <div
              key={idx}
              onClick={() => onSelect(item)}
              className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                isSelected ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{item.title || 'Untitled'}</p>
                  {item.authors && <p className="text-xs text-gray-500">{item.authors.join(', ')}</p>}
                  {item.publisher && <p className="text-xs text-gray-400">{item.publisher}</p>}
                </div>
                {conflicts > 0 && (
                  <span className="flex items-center gap-1 text-xs text-amber-600 shrink-0">
                    <AlertTriangle size={12} /> {conflicts} skipped
                  </span>
                )}
                {isSelected && <Check size={16} className="text-blue-600 shrink-0" />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FieldDiffConfirm({
  provider,
  candidate,
  diffs,
  applying,
  onConfirm,
  onCancel,
}: {
  provider: string;
  candidate: EnrichmentCandidate;
  diffs: FieldDiff[];
  applying: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const willApply = diffs.filter(d => d.willApply);
  const willSkip = diffs.filter(d => !d.willApply);

  return (
    <div className="border-2 border-blue-300 rounded-lg p-4 bg-blue-50 dark:bg-blue-900/10 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-sm">
          Confirm Enrichment — {provider === 'google_books' ? 'Google Books' : 'ComicVine'}
        </h3>
        <button onClick={onCancel} className="text-gray-400 hover:text-gray-600"><X size={16} /></button>
      </div>

      {/* Fields that WILL be applied */}
      {willApply.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-green-700 flex items-center gap-1">
            <Check size={12} /> Will be applied ({willApply.length} fields)
          </p>
          <div className="bg-green-50 dark:bg-green-900/20 rounded p-2 space-y-1.5">
            {willApply.map((d) => (
              <div key={d.field} className="flex items-center gap-2 text-xs">
                <span className="w-20 font-medium text-gray-600 shrink-0">{d.label}</span>
                <span className="text-gray-400 italic">empty</span>
                <ArrowRight size={10} className="text-green-600 shrink-0" />
                <span className="text-green-800 dark:text-green-300 truncate">{d.incomingValue}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fields that will be SKIPPED (conflicts) */}
      {willSkip.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-amber-700 flex items-center gap-1">
            <Shield size={12} /> Kept unchanged ({willSkip.length} fields — existing data preserved)
          </p>
          <div className="bg-amber-50 dark:bg-amber-900/20 rounded p-2 space-y-1.5">
            {willSkip.map((d) => (
              <div key={d.field} className="flex items-center gap-2 text-xs">
                <span className="w-20 font-medium text-gray-600 shrink-0">{d.label}</span>
                <span className="text-amber-800 dark:text-amber-300 truncate flex-1">
                  "{d.currentValue}" <span className="text-gray-400">(kept)</span>
                </span>
                <span className="text-gray-400 line-through truncate max-w-[120px]">{d.incomingValue}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 pl-1">Use Manual Edit to override existing values.</p>
        </div>
      )}

      {willApply.length === 0 && (
        <div className="flex items-start gap-2 p-2 bg-amber-50 dark:bg-amber-900/20 rounded text-xs text-amber-700">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <p>All source fields already have data. Nothing new will be applied. Use Manual Edit to override.</p>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={onConfirm}
          disabled={applying || willApply.length === 0}
          className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          {applying ? 'Applying...' : `Apply ${willApply.length} Field${willApply.length !== 1 ? 's' : ''}`}
        </button>
        <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
          Cancel
        </button>
      </div>
    </div>
  );
}
