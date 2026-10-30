import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  FileFormatIcon,
  FileFormatBadge,
  getDocumentFormat,
} from './FileFormatIcon';

describe('FileFormatIcon & FileFormatBadge', () => {
  it('detects PDF vs DOCX filenames accurately', () => {
    expect(getDocumentFormat('kHOA HỌC DỮ LIỆU - NHÓM 6.pdf')).toBe('pdf');
    expect(getDocumentFormat('CITRA_ACL_Sandbox_APA_10refs.PDF')).toBe('pdf');
    expect(getDocumentFormat('demo_29.09.docx')).toBe('docx');
    expect(getDocumentFormat('manuscript_final.DOCX')).toBe('docx');
    expect(getDocumentFormat('legacy.doc')).toBe('docx');
    expect(getDocumentFormat('')).toBe('pdf');
  });

  it('renders distinct PDF and DOCX vector logos and badges', () => {
    const { unmount } = render(
      <div>
        <FileFormatIcon filename="kHOA HỌC DỮ LIỆU - NHÓM 6.pdf" size="md" />
        <FileFormatBadge filename="kHOA HỌC DỮ LIỆU - NHÓM 6.pdf" />
      </div>,
    );
    expect(screen.getByTestId('file-format-icon-pdf')).toBeDefined();
    expect(screen.getByTestId('file-format-badge-pdf').textContent).toContain('PDF');
    unmount();

    render(
      <div>
        <FileFormatIcon filename="demo_29.09.docx" size="md" />
        <FileFormatBadge filename="demo_29.09.docx" />
      </div>,
    );
    expect(screen.getByTestId('file-format-icon-docx')).toBeDefined();
    expect(screen.getByTestId('file-format-badge-docx').textContent).toContain('DOCX');
  });
});
