import { useState } from 'react';
import { FileText, Folder, FolderOpen, ChevronRight, ChevronDown } from 'lucide-react';
import type { DocumentTree, DocumentNode } from '../../types';

interface DocumentTreeViewerProps {
  documentTree: DocumentTree | null;
  activeDocument?: string;
  onDocumentSelect?: (path: string) => void;
}

interface TreeNodeProps {
  node: DocumentNode;
  level: number;
  activeDocument?: string;
  onDocumentSelect?: (path: string) => void;
}

function TreeNode({ node, level, activeDocument, onDocumentSelect }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(level === 0 || level === 1);
  const isActive = activeDocument === node.path;

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(1)} MB`;
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-gray-700" />;
      case 'docx':
      case 'doc':
        return <FileText className="w-4 h-4 text-gray-700" />;
      case 'xlsx':
      case 'xls':
        return <FileText className="w-4 h-4 text-gray-700" />;
      case 'txt':
        return <FileText className="w-4 h-4 text-gray-700" />;
      default:
        return <FileText className="w-4 h-4 text-gray-700" />;
    }
  };

  if (node.type === 'folder') {
    return (
      <div>
        <div
          className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-blue-50 transition-colors ${isActive ? 'bg-blue-100' : ''
            }`}
          style={{ paddingLeft: `${level * 12 + 8}px` }}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-600" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-600" />
            )}
          </div>
          <div className="flex-shrink-0">
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 text-gray-700" />
            ) : (
              <Folder className="w-4 h-4 text-gray-700" />
            )}
          </div>
          <span className="text-sm text-gray-800 truncate">{node.name}</span>
        </div>

        {isExpanded && node.children && (
          <div>
            {node.children.map((child, index) => (
              <TreeNode
                key={`${child.path}-${index}`}
                node={child}
                level={level + 1}
                activeDocument={activeDocument}
                onDocumentSelect={onDocumentSelect}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // File node
  return (
    <div
      className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-blue-50 transition-colors group ${isActive ? 'bg-blue-100 ring-1 ring-blue-500' : ''
        }`}
      style={{ paddingLeft: `${level * 12 + 32}px` }}
      onClick={() => onDocumentSelect?.(node.path)}
      title={`${node.name}${node.size ? ` - ${formatFileSize(node.size)}` : ''}${node.page_count ? ` - ${node.page_count} pages` : ''
        }`}
    >
      <div className="flex-shrink-0">{getFileIcon(node.name)}</div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-gray-800 truncate">{node.name}</div>
        <div className="text-xs text-gray-500 flex items-center gap-2">
          {node.size && <span>{formatFileSize(node.size)}</span>}
          {node.page_count && (
            <>
              {node.size && <span>•</span>}
              <span>{node.page_count} pages</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export function DocumentTreeViewer({
  documentTree,
  activeDocument,
  onDocumentSelect,
}: DocumentTreeViewerProps) {
  if (!documentTree) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm">
        <div className="text-center">
          <Folder className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No documents loaded</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 border-b border-gray-200 sticky top-0 bg-white/95 backdrop-blur-sm z-10">
        <h3 className="text-sm font-semibold text-gray-800">Documents</h3>
        {documentTree.total_files !== undefined && (
          <p className="text-xs text-gray-600 mt-1">
            {documentTree.total_files} file{documentTree.total_files !== 1 ? 's' : ''}
            {documentTree.total_size && (
              <> • {(documentTree.total_size / 1024 / 1024).toFixed(2)} MB</>
            )}
          </p>
        )}
      </div>

      <div className="p-2">
        {documentTree.documents.map((node, index) => (
          <TreeNode
            key={`${node.path}-${index}`}
            node={node}
            level={0}
            activeDocument={activeDocument}
            onDocumentSelect={onDocumentSelect}
          />
        ))}
      </div>
    </div>
  );
}
