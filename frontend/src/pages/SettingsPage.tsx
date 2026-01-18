import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Header, Button, ImportWizard, Modal } from '../components';
import { GoogleSignInButton } from '../components/GoogleSignInButton';
import { apiClient, ApiClientError } from '../api/client';
import type { UserProfileResponse } from '../types';

type LinkingStatus = 'idle' | 'loading' | 'success' | 'error';
type ClearStatus = 'idle' | 'confirming' | 'clearing' | 'success' | 'error';

interface LinkingError {
  code: string;
  message: string;
}

const ERROR_MESSAGES: Record<string, string> = {
  cancelled: 'Google linking was cancelled.',
  invalid_state: 'Session expired. Please try again.',
  invalid_request: 'Invalid request. Please try again.',
  invalid_flow: 'Invalid linking flow. Please try again.',
  user_not_found: 'User not found. Please log in again.',
  token_exchange_failed: 'Failed to verify with Google. Please try again.',
  no_id_token: 'No authentication data received from Google.',
  invalid_token: 'Invalid authentication from Google. Please try again.',
  email_not_verified: 'Your Google email is not verified.',
  already_linked_other: 'This Google account is already linked to another account.',
};

/**
 * Settings page allowing users to manage their account settings,
 * including linking their Google account.
 */
export function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);

  const [linkingStatus, setLinkingStatus] = useState<LinkingStatus>('idle');
  const [linkingError, setLinkingError] = useState<LinkingError | null>(null);

  // Import wizard state
  const [showImportWizard, setShowImportWizard] = useState(false);

  // Clear all rankings state
  const [clearStatus, setClearStatus] = useState<ClearStatus>('idle');
  const [clearError, setClearError] = useState<string | null>(null);

  // Fetch user profile on mount
  const fetchProfile = useCallback(async () => {
    setIsLoadingProfile(true);
    setProfileError(null);

    try {
      const data = await apiClient.getCurrentUser();
      setProfile(data);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setProfileError(err.message);
      } else {
        setProfileError('Failed to load profile');
      }
    } finally {
      setIsLoadingProfile(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  // Handle callback query params from Google linking
  useEffect(() => {
    const linked = searchParams.get('linked');
    const error = searchParams.get('error');

    if (linked === 'success') {
      setLinkingStatus('success');
      // Clear the query params
      setSearchParams({}, { replace: true });
      // Refresh profile to show updated status
      fetchProfile();
    } else if (error) {
      setLinkingStatus('error');
      setLinkingError({
        code: error,
        message: ERROR_MESSAGES[error] || 'An error occurred during linking.',
      });
      // Clear the query params
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams, fetchProfile]);

  const handleLinkGoogle = useCallback(async () => {
    setLinkingStatus('loading');
    setLinkingError(null);

    try {
      const response = await apiClient.getGoogleLinkUrl();
      // Redirect to Google OAuth
      window.location.href = response.authorization_url;
    } catch (err) {
      setLinkingStatus('error');
      if (err instanceof ApiClientError) {
        if (err.status === 409) {
          setLinkingError({
            code: 'already_linked',
            message: 'Your account is already linked to Google.',
          });
        } else {
          setLinkingError({
            code: 'api_error',
            message: err.message,
          });
        }
      } else {
        setLinkingError({
          code: 'unknown',
          message: 'Failed to initiate Google linking.',
        });
      }
    }
  }, []);

  const dismissSuccess = useCallback(() => {
    setLinkingStatus('idle');
  }, []);

  const dismissError = useCallback(() => {
    setLinkingStatus('idle');
    setLinkingError(null);
  }, []);

  const handleImportComplete = useCallback(() => {
    // Optionally refresh data or show success message
    // For now, just close the wizard
  }, []);

  const handleClearAllClick = useCallback(() => {
    setClearStatus('confirming');
    setClearError(null);
  }, []);

  const handleClearAllCancel = useCallback(() => {
    setClearStatus('idle');
    setClearError(null);
  }, []);

  const handleClearAllConfirm = useCallback(async () => {
    setClearStatus('clearing');
    setClearError(null);

    try {
      await apiClient.clearAllRankings();
      setClearStatus('success');
    } catch (err) {
      setClearStatus('error');
      if (err instanceof ApiClientError) {
        setClearError(err.message);
      } else {
        setClearError('Failed to clear rankings. Please try again.');
      }
    }
  }, []);

  const handleClearSuccessDismiss = useCallback(() => {
    setClearStatus('idle');
  }, []);

  return (
    <>
      <Header />
      <main className="main-layout">
        <div className="container">
          <div className="page-content">
            <div className="page-header">
              <h1 className="page-title">Settings</h1>
            </div>

            {/* Success Alert */}
            {linkingStatus === 'success' && (
              <div className="alert alert-success" role="alert">
                <span>Google account linked successfully!</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={dismissSuccess}
                  style={{ marginLeft: 'var(--space-2)' }}
                >
                  Dismiss
                </Button>
              </div>
            )}

            {/* Error Alert */}
            {linkingStatus === 'error' && linkingError && (
              <div className="alert alert-error" role="alert">
                <span>{linkingError.message}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={dismissError}
                  style={{ marginLeft: 'var(--space-2)' }}
                >
                  Dismiss
                </Button>
              </div>
            )}

            {/* Profile Error */}
            {profileError && (
              <div className="alert alert-error" role="alert">
                <span>{profileError}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={fetchProfile}
                  style={{ marginLeft: 'var(--space-2)' }}
                >
                  Retry
                </Button>
              </div>
            )}

            {/* Loading State */}
            {isLoadingProfile && (
              <div className="loading-container">
                <div className="spinner" />
              </div>
            )}

            {/* Settings Content */}
            {!isLoadingProfile && profile && (
              <div className="settings-content">
                {/* Account Section */}
                <section className="settings-section">
                  <h2 className="settings-section-title">Account</h2>
                  <div className="settings-card">
                    <div className="settings-row">
                      <div className="settings-label">Email</div>
                      <div className="settings-value">{profile.email}</div>
                    </div>
                    <div className="settings-row">
                      <div className="settings-label">Account Type</div>
                      <div className="settings-value">
                        {profile.auth_provider === 'local' && 'Email & Password'}
                        {profile.auth_provider === 'google' && 'Google Account'}
                        {profile.auth_provider === 'linked' && 'Email & Google Linked'}
                      </div>
                    </div>
                  </div>
                </section>

                {/* Connected Accounts Section */}
                <section className="settings-section">
                  <h2 className="settings-section-title">Connected Accounts</h2>
                  <div className="settings-card">
                    <div className="settings-row settings-row-action">
                      <div className="settings-row-info">
                        <div className="settings-label">Google</div>
                        <div className="settings-description">
                          {profile.has_google_linked
                            ? 'Your Google account is linked. You can sign in with Google.'
                            : 'Link your Google account to enable Google sign-in.'}
                        </div>
                      </div>
                      <div className="settings-row-action-button">
                        {profile.has_google_linked ? (
                          <span className="badge badge-success">Connected</span>
                        ) : (
                          <GoogleSignInButton
                            variant="signin"
                            onClick={handleLinkGoogle}
                            loading={linkingStatus === 'loading'}
                            disabled={linkingStatus === 'loading'}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                </section>

                {/* Login Methods Section */}
                <section className="settings-section">
                  <h2 className="settings-section-title">Login Methods</h2>
                  <div className="settings-card">
                    <div className="settings-row">
                      <div className="settings-label">Password Login</div>
                      <div className="settings-value">
                        {profile.has_password ? (
                          <span className="badge badge-success">Enabled</span>
                        ) : (
                          <span className="badge badge-neutral">Not Set</span>
                        )}
                      </div>
                    </div>
                    <div className="settings-row">
                      <div className="settings-label">Google Login</div>
                      <div className="settings-value">
                        {profile.has_google_linked ? (
                          <span className="badge badge-success">Enabled</span>
                        ) : (
                          <span className="badge badge-neutral">Not Linked</span>
                        )}
                      </div>
                    </div>
                  </div>
                </section>

                {/* Import Watch History Section */}
                <section className="settings-section">
                  <h2 className="settings-section-title">Import Watch History</h2>
                  <div className="settings-card">
                    <div className="settings-row settings-row-action">
                      <div className="settings-row-info">
                        <div className="settings-label">Amazon Prime Video</div>
                        <div className="settings-description">
                          Import your watch history from Amazon Prime Video using a CSV export.
                        </div>
                      </div>
                      <div className="settings-row-action-button">
                        <Button onClick={() => setShowImportWizard(true)}>
                          Import
                        </Button>
                      </div>
                    </div>
                  </div>
                </section>

                {/* Data Management Section */}
                <section className="settings-section">
                  <h2 className="settings-section-title">Data Management</h2>
                  <div className="settings-card settings-card-danger">
                    {clearStatus === 'success' && (
                      <div className="alert alert-success" role="alert" style={{ marginBottom: 'var(--space-4)' }}>
                        <span>All rankings have been cleared.</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleClearSuccessDismiss}
                          style={{ marginLeft: 'var(--space-2)' }}
                        >
                          Dismiss
                        </Button>
                      </div>
                    )}
                    {clearStatus === 'error' && clearError && (
                      <div className="alert alert-error" role="alert" style={{ marginBottom: 'var(--space-4)' }}>
                        <span>{clearError}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleClearAllCancel}
                          style={{ marginLeft: 'var(--space-2)' }}
                        >
                          Dismiss
                        </Button>
                      </div>
                    )}
                    <div className="settings-row settings-row-action">
                      <div className="settings-row-info">
                        <div className="settings-label">Clear All Rankings</div>
                        <div className="settings-description">
                          Permanently delete all your movie rankings. This action cannot be undone.
                        </div>
                      </div>
                      <div className="settings-row-action-button">
                        <Button
                          variant="danger"
                          onClick={handleClearAllClick}
                          disabled={clearStatus === 'clearing'}
                        >
                          Clear All
                        </Button>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Import Wizard Modal */}
      {showImportWizard && (
        <ImportWizard
          onClose={() => setShowImportWizard(false)}
          onComplete={handleImportComplete}
        />
      )}

      {/* Clear All Confirmation Modal */}
      <Modal
        isOpen={clearStatus === 'confirming' || clearStatus === 'clearing'}
        onClose={handleClearAllCancel}
        title="Clear All Rankings"
      >
        <div className="clear-all-modal">
          <p className="clear-all-modal-message">
            Are you sure you want to delete all your movie rankings? This action
            cannot be undone.
          </p>
          <div className="clear-all-modal-actions">
            <Button
              variant="secondary"
              onClick={handleClearAllCancel}
              disabled={clearStatus === 'clearing'}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleClearAllConfirm}
              loading={clearStatus === 'clearing'}
              disabled={clearStatus === 'clearing'}
            >
              {clearStatus === 'clearing' ? 'Clearing...' : 'Clear All Rankings'}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
