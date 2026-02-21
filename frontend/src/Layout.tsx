import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext'
import './Layout.css'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="layout">
      <nav className="nav">
        <div className="nav-links">
          <Link to="/home">Home</Link>
          <Link to="/reports">Reports</Link>
          <Link to="/settings">Settings</Link>
        </div>
        <button type="button" className="nav-logout" onClick={handleLogout}>
          Log out
        </button>
      </nav>
      <main className="main">{children}</main>
    </div>
  )
}
