import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

type CallbackState = 'loading' | 'success' | 'error';

interface ErrorInfo {
  title: string;
  message: string;
  canRetry: boolean;
}

/**
 * Handles the OAuth callback after Google authentication.
 * The backend sets the httpOnly session cookie before redirecting here, so the
 * URL carries no credential; this page only confirms the session via /auth/me/.
 */
export function GoogleCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { refreshAuth, isAuthenticated, isLoading } = useAuth();

  const [state, setState] = useState<CallbackState>('loading');
  const [errorInfo, setErrorInfo] = useState<ErrorInfo | null>(null);

  useEffect(() => {
    // Wait for the initial session check, then bounce signed-in users home.
    if (isLoading) return;
    if (isAuthenticated) {
      navigate('/', { replace: true });
      return;
    }

    // Error from backend or Google
    const error = searchParams.get('error');
    if (error) {
      const errorDescription = searchParams.get('error_description');
      setState('error');
      setErrorInfo({
        title: 'Authentication Failed',
        message: errorDescription || error || 'Sign-in failed. Please try again.',
        canRetry: true,
      });
      return;
    }

    let cancelled = false;
    void refreshAuth().then((ok) => {
      if (cancelled) return;
      if (!ok) {
        setState('error');
        setErrorInfo({
          title: 'Invalid Callback',
          message: 'We could not confirm your sign-in. Please try signing in again.',
          canRetry: true,
        });
        return;
      }
      setState('success');
      // Brief delay for visual feedback before leaving the page
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 500);
    });
    return () => {
      cancelled = true;
    };
  }, [searchParams, refreshAuth, navigate, isAuthenticated, isLoading]);

  return (
    <div className="auth-layout">
      <div className="auth-card">
        {state === 'loading' && (
          <div className="callback-loading">
            <div className="spinner spinner-lg" aria-hidden="true" />
            <h2 className="callback-title">Signing you in...</h2>
            <p className="callback-message">Please wait while we complete your sign-in.</p>
          </div>
        )}

        {state === 'success' && (
          <div className="callback-success">
            <div className="callback-icon callback-icon-success" aria-hidden="true">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
            <h2 className="callback-title">Success!</h2>
            <p className="callback-message">Redirecting you to your rankings...</p>
          </div>
        )}

        {state === 'error' && errorInfo && (
          <div className="callback-error">
            <div className="callback-icon callback-icon-error" aria-hidden="true">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
              </svg>
            </div>
            <h2 className="callback-title">{errorInfo.title}</h2>
            <p className="callback-message">{errorInfo.message}</p>

            {errorInfo.canRetry && (
              <div className="callback-actions">
                <Link to="/login" className="btn btn-primary">
                  Try Again
                </Link>
                <Link to="/login" className="btn btn-ghost">
                  Back to Login
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
