import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import '@/i18n';
import { LoginPage } from './LoginPage';

function renderLoginPage(loginMock = vi.fn().mockResolvedValue(undefined)) {
  return {
    loginMock,
    ...render(
      <ThemeProvider defaultTheme="light">
        <MemoryRouter initialEntries={['/login']}>
          <AuthContext.Provider
            value={{
              user: null,
              token: null,
              isAdmin: false,
              isLoading: false,
              login: loginMock,
              logout: async () => {},
              refreshUser: async () => {},
            }}
          >
            <LoginPage />
          </AuthContext.Provider>
        </MemoryRouter>
      </ThemeProvider>
    ),
  };
}

describe('LoginPage', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('renders brand showcase and form inputs', () => {
    renderLoginPage();

    expect(
      screen.getByRole('heading', { name: /welcome back|chào mừng trở lại/i })
    ).toBeDefined();
    expect(screen.getByLabelText(/username|tên đăng nhập/i)).toBeDefined();
    expect(screen.getByLabelText(/password|mật khẩu/i)).toBeDefined();
    expect(
      screen.getByRole('button', { name: /sign in|đăng nhập/i })
    ).toBeDefined();
    expect(screen.getByText(/symbolic_verifier\.py/i)).toBeDefined();
  });

  it('toggles password visibility when clicking the eye button', () => {
    renderLoginPage();

    const passwordInput = screen.getByLabelText(
      /password|mật khẩu/i
    ) as HTMLInputElement;
    expect(passwordInput.type).toBe('password');

    const toggleBtn = screen.getByRole('button', { name: /show characters/i });
    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe('text');

    const hideBtn = screen.getByRole('button', { name: /hide characters/i });
    fireEvent.click(hideBtn);
    expect(passwordInput.type).toBe('password');
  });

  it('submits credentials and calls login()', async () => {
    const loginMock = vi.fn().mockResolvedValue(undefined);
    renderLoginPage(loginMock);

    fireEvent.change(screen.getByLabelText(/username|tên đăng nhập/i), {
      target: { value: 'admin' },
    });
    fireEvent.change(screen.getByLabelText(/password|mật khẩu/i), {
      target: { value: 'admin123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in|đăng nhập/i }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('admin', 'admin123');
    });
  });

  it('displays destructive alert when login fails', async () => {
    const loginMock = vi
      .fn()
      .mockRejectedValue(new Error('Invalid username or password'));
    renderLoginPage(loginMock);

    fireEvent.change(screen.getByLabelText(/username|tên đăng nhập/i), {
      target: { value: 'wrong' },
    });
    fireEvent.change(screen.getByLabelText(/password|mật khẩu/i), {
      target: { value: 'wrongpass' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in|đăng nhập/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid username or password')).toBeDefined();
    });
  });
});
