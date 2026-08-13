"use client";

import { Button } from "nhsuk-react-components";

export interface PaginationControlsProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

/**
 * Accessible previous/next pagination. Buttons are disabled at the bounds and
 * the current page is announced via `aria-live`.
 */
export function PaginationControls({ page, totalPages, onPageChange }: PaginationControlsProps) {
  if (totalPages <= 1) return null;

  return (
    <nav className="clerkstone-pagination" role="navigation" aria-label="Pagination">
      <Button
        secondary
        small
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      <span className="nhsuk-body-s" aria-live="polite">
        Page {page} of {totalPages}
      </span>
      <Button
        secondary
        small
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </nav>
  );
}
