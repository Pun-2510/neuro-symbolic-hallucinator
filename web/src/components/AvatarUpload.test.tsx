import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@/test-utils';
import { AvatarUpload } from './AvatarUpload';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    api: {
      ...actual.api,
      uploadMyAvatar: vi.fn().mockResolvedValue({
        id: 1,
        username: 'admin',
        email: 'admin@tdtu.edu.vn',
        full_name: 'Admin',
        role: 'admin',
        is_active: true,
        avatar_url: '/api/avatars/1.png?v=123',
        created_at: new Date().toISOString(),
        last_login_at: null,
      }),
    },
  };
});

describe('AvatarUpload', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('shows adjust and change buttons when an avatar is already uploaded and allows dragging/zooming', () => {
    const onSuccess = vi.fn();
    render(<AvatarUpload currentAvatarUrl="/api/avatars/1.png" onSuccess={onSuccess} size="lg" />);

    const adjustBtn = screen.getByTestId('avatar-adjust-btn');
    expect(adjustBtn).toBeDefined();

    // Enter adjust mode via button
    fireEvent.click(adjustBtn);

    const zoomSlider = screen.getByTestId('avatar-zoom-slider') as HTMLInputElement;
    expect(zoomSlider).toBeDefined();

    // Change zoom
    fireEvent.change(zoomSlider, { target: { value: '1.5' } });
    expect(zoomSlider.value).toBe('1.5');

    // Drag viewport with mouse events
    const viewport = screen.getByTestId('avatar-crop-viewport');
    fireEvent.mouseDown(viewport, { clientX: 50, clientY: 50, button: 0 });
    fireEvent.mouseMove(window, { clientX: 70, clientY: 65 });
    fireEvent.mouseUp(window, { clientX: 70, clientY: 65 });

    const img = screen.getByAltText('Avatar preview') as HTMLImageElement;
    expect(img.style.transform).toContain('20px');
    expect(img.style.transform).toContain('15px');
  });

  it('enters adjust mode automatically when dragging on existing avatar', () => {
    const onSuccess = vi.fn();
    render(<AvatarUpload currentAvatarUrl="/api/avatars/1.png" onSuccess={onSuccess} size="lg" />);

    const viewport = screen.getByTestId('avatar-crop-viewport');
    fireEvent.mouseDown(viewport, { clientX: 60, clientY: 60, button: 0 });
    fireEvent.mouseMove(window, { clientX: 75, clientY: 80 });
    fireEvent.mouseUp(window, { clientX: 75, clientY: 80 });

    expect(screen.getByTestId('avatar-zoom-slider')).toBeDefined();
    expect(screen.getByTestId('avatar-save-btn')).toBeDefined();
  });
});
