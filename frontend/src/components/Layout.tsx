import { useState, useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import {
  LayoutDashboard, MessageSquare, FileText, Bot, GitBranch,
  Palette, Database, BarChart3, Puzzle, Settings, LogOut,
  Menu, X, Folder, LayoutTemplate, Shield, Sun, Moon, Monitor,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/chat', icon: MessageSquare, label: 'AI Chat' },
  { to: '/content', icon: FileText, label: 'Content' },
  { to: '/projects', icon: Folder, label: 'Projects' },
  { to: '/templates', icon: LayoutTemplate, label: 'Templates' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/workflows', icon: GitBranch, label: 'Workflows' },
  { to: '/brands', icon: Palette, label: 'Brands' },
  { to: '/memory', icon: Database, label: 'Memory' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/plugins', icon: Puzzle, label: 'Plugins' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const { effectiveTheme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const closeMobile = () => setMobileMenuOpen(false)

  useEffect(() => {
    const handler = () => setMobileMenuOpen(false)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors duration-200 ${
      isActive
        ? 'bg-brand-600/20 text-brand-400 border border-brand-600/30 font-medium'
        : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200 border border-transparent'
    } ${!sidebarOpen ? 'justify-center' : ''}`

  const mobileNavLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors duration-200 ${
      isActive
        ? 'bg-brand-600/20 text-brand-400 border border-brand-600/30 font-medium'
        : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200 border border-transparent'
    }`

  const filteredItems = user?.role === 'admin'
    ? [...navItems, { to: '/admin', icon: Shield, label: 'Admin' }]
    : navItems

  const themeIcon = effectiveTheme === 'dark' ? Moon : effectiveTheme === 'light' ? Sun : Monitor

  const ThemeIcon = themeIcon

  const sidebarContent = (
    <>
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-800">
        {sidebarOpen && (
          <span className="text-lg font-bold text-brand-400">AI Content OS</span>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hidden md:block"
        >
          {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
        <button
          onClick={closeMobile}
          className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 md:hidden"
        >
          <X size={18} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        {filteredItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={closeMobile}
            className={sidebarOpen ? navLinkClass : mobileNavLinkClass}
          >
            <item.icon size={20} />
            {sidebarOpen && <span className="text-sm font-medium">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-gray-800 p-4">
        {sidebarOpen ? (
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-200 truncate">{user?.name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
            <button onClick={handleLogout} className="p-2 rounded-lg hover:bg-gray-800 text-gray-400" title="Logout">
              <LogOut size={18} />
            </button>
          </div>
        ) : (
          <button onClick={handleLogout} className="w-full flex justify-center p-2 rounded-lg hover:bg-gray-800 text-gray-400" title="Logout">
            <LogOut size={18} />
          </button>
        )}
      </div>
    </>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-gray-900 border-r border-gray-800 flex-col transition-all duration-300 hidden md:flex`}>
        {sidebarContent}
      </aside>

      {/* Mobile Sidebar Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={closeMobile} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {/* Mobile header bar */}
        <div className="flex items-center gap-3 px-4 h-14 border-b border-gray-800 md:hidden bg-gray-900">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-400"
          >
            <Menu size={20} />
          </button>
          <span className="text-sm font-bold text-brand-400">AI Content OS</span>
        </div>

        {/* Header with theme toggle */}
        <div className="hidden md:flex items-center justify-end px-8 py-3">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-200 transition-colors"
            title={`Theme: ${effectiveTheme} (click to cycle)`}
          >
            <ThemeIcon size={18} />
          </button>
        </div>

        <div className="p-4 md:p-8 max-w-7xl mx-auto page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
