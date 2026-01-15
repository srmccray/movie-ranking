import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from './Button';

export function Header() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <span className="header-logo">Movie Ranking</span>
          {isAuthenticated && (
            <nav className="header-nav">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `header-nav-link ${isActive ? 'header-nav-link-active' : ''}`
                }
              >
                Rankings
              </NavLink>
              <NavLink
                to="/analytics"
                className={({ isActive }) =>
                  `header-nav-link ${isActive ? 'header-nav-link-active' : ''}`
                }
              >
                Analytics
              </NavLink>
              <NavLink
                to="/settings"
                className={({ isActive }) =>
                  `header-nav-link ${isActive ? 'header-nav-link-active' : ''}`
                }
              >
                Settings
              </NavLink>
            </nav>
          )}
        </div>
        {isAuthenticated && (
          <Button variant="ghost" size="sm" onClick={logout}>
            Logout
          </Button>
        )}
      </div>
    </header>
  );
}
