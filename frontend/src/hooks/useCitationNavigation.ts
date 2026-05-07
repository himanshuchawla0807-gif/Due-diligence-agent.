import { useState } from 'react';
import type { Citation } from '../types';

export function useCitationNavigation() {
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [isViewerOpen, setIsViewerOpen] = useState(false);

  const handleCitationClick = (citation: Citation) => {
    setActiveCitation(citation);
    setIsViewerOpen(true);
  };

  const closeViewer = () => {
    setIsViewerOpen(false);
    // Keep activeCitation for potential re-opening
    // Clear it after a short delay to allow for exit animations
    setTimeout(() => {
      setActiveCitation(null);
    }, 300);
  };

  return {
    activeCitation,
    isViewerOpen,
    handleCitationClick,
    closeViewer
  };
}
