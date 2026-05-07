/**
 * TypeScript type definitions for Citation-Aware RAG
 */

// Citation types
export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Citation {
  id: string;
  file_name: string;
  relative_path: string;
  page: number;
  bbox?: number[]; // Optional bounding box [x1, y1, x2, y2]
  text_snippet?: string;
  uri?: string; // Optional URI for Gemini files
  full_context?: string; // Optional extended context
}

export interface Source {
  content: string;
  metadata: any;
  score?: number;
}

// Graph agent step types
export interface GraphStep {
  action: string;
  tool_input: string;
  observation: string;
}

// Chat message types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  citations?: Citation[];
  sources?: Source[];
  industry?: "PE" | "VC" | "FO" | "MA" | "CA" | "OTHER" | null;
  steps?: GraphStep[];
  withSearch?: boolean;
}

// Document tree types
export interface DocumentNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  size?: number;
  page_count?: number;
  children?: DocumentNode[];
}

export interface DocumentTree {
  session_id: string;
  documents: DocumentNode[];
  total_files?: number;
  total_size?: number;
}

// API response types
export interface ChatResponse {
  response: string;
  status: string;
  sources?: any[];
  citations?: Citation[];
  steps?: GraphStep[];
}

export interface DocumentTreeResponse {
  session_id: string;
  documents: DocumentNode[];
  total_files: number;
  total_size: number;
}

// Component props types
export interface SplitScreenLayoutProps {
  messages: ChatMessage[];
  documentTree: DocumentTree | null;
  onCitationClick: (citation: Citation) => void;
  onSendMessage: (message: string, withSearch: boolean) => void;
  isLoading: boolean;
}

export interface DocumentTreeViewerProps {
  documentTree: DocumentTree | null;
  activeDocument?: string;
  onDocumentSelect?: (path: string) => void;
}

export interface ChatMessagesPanelProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (message: string, withSearch: boolean) => void;
  onCitationClick: (citation: Citation) => void;
}

export interface CitationAwareResponseProps {
  content: string;
  citations: Citation[];
  onCitationClick: (citation: Citation) => void;
  onDocumentSelect?: (documentPath: string) => void;
}

export interface DocumentViewerProps {
  sessionId: string;
  fileName: string;
  citation: Citation;
  onClose: () => void;
}

// Hook return types
export interface UseCitationNavigation {
  activeCitation: Citation | null;
  isViewerOpen: boolean;
  handleCitationClick: (citation: Citation) => void;
  closeViewer: () => void;
}

export interface UseDocumentTree {
  documentTree: DocumentTree | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}
