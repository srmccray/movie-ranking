import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from './Button';

export function Header() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <header className="header">
      <div className="header-content">
        <Link to="/" className="header-logo">
          Movie Ranking
        </Link>
        {isAuthenticated && (
          <Button variant="ghost" size="sm" onClick={logout}>
            Logout
          </Button>
        )}
      </div>
    </header>
  );
}
