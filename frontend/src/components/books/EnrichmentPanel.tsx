import { useState, useEffect } from 'react';
import { enrichmentApi, EnrichmentCandidate } from '@/api/enrichment';
import { AlertTriangle, Check, RefreshCw, Edit3, X } from 'lucide-react';
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

  const getConflicts = (candidate: EnrichmentCandidate): string[] => {
    if (!metadata) return [];
    const conflicts: string[] = [];
    if (metadata.source_title && candidate.title && metadata.source_title !== candidate.title) {
      conflicts.push('title');
    }
    if (metadata.source_author && candidate.authors?.length) {
      const incoming = candidate.authors.join(', ');
      if (metadata.source_author !== incoming) conflicts.push('author');
    }
    if (metadata.source_publisher && candidate.publisher && metadata.source_publisher !== candidate.publisher) {
      conflicts.push('publisher');
    }
    if (metadata.source_isbn && (candidate.isbn_13 || candidate.isbn_10)) {
      const incoming = candidate.isbn_13 || candidate.isbn_10;
      if (metadata.source_isbn !== incoming) conflicts.push('isbn');
    }
    return conflicts;
  };

  const applyCandidate = async () => {
    if (!selectedCandidate) return;
    setApplying(true);
    try {
      await enrichmentApi.apply(bookId, selectedCandidate.provider, selectedCandidate.candidate);
      toast.success('Enrichment applied');
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
      toast.success('Metadata calibrated');
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
          {metadata.last_calibrated_at && (
            <p><span className="font-medium">Last calibrated:</span> {new Date(metadata.last_calibrated_at).toLocaleString()}</p>
          )}
        </div>
      )}

      {/* Manual edit form */}
      {editMode && (
        <div className="border rounded-lg p-4 space-y-3 bg-white dark:bg-gray-900">
          <h3 className="font-medium text-sm">Calibrate Metadata (Manual Edit)</h3>
          <p className="text-xs text-gray-500">Changes are audited. Only fill fields you want to override.</p>
          {Object.entries(editForm).map(([key, val]) => (
            <div key={key} className="flex items-center gap-2">
              <label className="w-28 text-xs font-medium text-gray-600 shrink-0">
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
              provider="google_books"
              items={candidates.google_books}
              selected={selectedCandidate?.provider === 'google_books' ? selectedCandidate.candidate : null}
              onSelect={(c) => handleSelectCandidate('google_books', c)}
              getConflicts={getConflicts}
            />
          )}
          {candidates.comicvine.length > 0 && (
            <CandidateList
              title="ComicVine"
              provider="comicvine"
              items={candidates.comicvine}
              selected={selectedCandidate?.provider === 'comicvine' ? selectedCandidate.candidate : null}
              onSelect={(c) => handleSelectCandidate('comicvine', c)}
              getConflicts={getConflicts}
            />
          )}
          {candidates.google_books.length === 0 && candidates.comicvine.length === 0 && (
            <p className="text-sm text-gray-500">No enrichment candidates found.</p>
          )}
        </div>
      )}

      {/* Confirmation dialog */}
      {selectedCandidate && (
        <ConfirmDialog
          provider={selectedCandidate.provider}
          candidate={selectedCandidate.candidate}
          conflicts={getConflicts(selectedCandidate.candidate)}
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
  getConflicts,
}: {
  title: string;
  provider: string;
  items: EnrichmentCandidate[];
  selected: EnrichmentCandidate | null;
  onSelect: (c: EnrichmentCandidate) => void;
  getConflicts: (c: EnrichmentCandidate) => string[];
}) {
  return (
    <div>
      <h3 className="text-sm font-medium mb-2">{title} Results</h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {items.map((item, idx) => {
          const conflicts = getConflicts(item);
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
                {conflicts.length > 0 && (
                  <span className="flex items-center gap-1 text-xs text-amber-600 shrink-0">
                    <AlertTriangle size={12} /> {conflicts.length} conflict{conflicts.length > 1 ? 's' : ''}
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

function ConfirmDialog({
  provider,
  candidate,
  conflicts,
  applying,
  onConfirm,
  onCancel,
}: {
  provider: string;
  candidate: EnrichmentCandidate;
  conflicts: string[];
  applying: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="border-2 border-blue-300 rounded-lg p-4 bg-blue-50 dark:bg-blue-900/10 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-sm">Confirm Enrichment from {provider === 'google_books' ? 'Google Books' : 'ComicVine'}</h3>
        <button onClick={onCancel} className="text-gray-400 hover:text-gray-600"><X size={16} /></button>
      </div>

      <div className="text-xs space-y-1">
        {candidate.title && <p><span className="font-medium">Title:</span> {candidate.title}</p>}
        {candidate.authors && <p><span className="font-medium">Authors:</span> {candidate.authors.join(', ')}</p>}
        {candidate.description && <p><span className="font-medium">Description:</span> {candidate.description.slice(0, 200)}...</p>}
        {candidate.publisher && <p><span className="font-medium">Publisher:</span> {candidate.publisher}</p>}
        {candidate.language && <p><span className="font-medium">Language:</span> {candidate.language}</p>}
        {(candidate.isbn_13 || candidate.isbn_10) && <p><span className="font-medium">ISBN:</span> {candidate.isbn_13 || candidate.isbn_10}</p>}
        {candidate.published_date && <p><span className="font-medium">Published:</span> {candidate.published_date}</p>}
      </div>

      {conflicts.length > 0 && (
        <div className="flex items-start gap-2 p-2 bg-amber-50 dark:bg-amber-900/20 rounded text-xs text-amber-700 dark:text-amber-400">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Conflicts detected</p>
            <p>Fields with existing data that won't be overwritten: {conflicts.join(', ')}</p>
            <p className="mt-1">Only empty source fields will be populated. Use Manual Edit to override.</p>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={onConfirm}
          disabled={applying}
          className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          {applying ? 'Applying...' : 'Apply Enrichment'}
        </button>
        <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
          Cancel
        </button>
      </div>
    </div>
  );
}
