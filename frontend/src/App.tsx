import { Routes, Route, Navigate, useParams } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'
import Layout from './Layout'
import Login from './pages/Login'
import Home from './pages/Home'
import Draft from './pages/Draft'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import Rules from './pages/Rules'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/" replace />
  return <>{children}</>
}

function QueueRedirect() {
  const { month } = useParams<{ month: string }>()
  return <Navigate to={`/review/${month ?? ''}`} replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/home"
        element={
          <ProtectedRoute>
            <Layout><Home /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/review/:month"
        element={
          <ProtectedRoute>
            <Layout><Draft /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/review/:month/queue"
        element={
          <ProtectedRoute>
            <QueueRedirect />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <Layout><Reports /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/rules"
        element={
          <ProtectedRoute>
            <Layout><Rules /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Layout><Settings /></Layout>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
