import { Navigate, Route, Routes, useParams } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import Home from '@/pages/Home'
import Workspace from '@/pages/Workspace'

/** Keyed by project id so switching projects remounts with fresh state (and flushes pending saves). */
function ProjectRoute() {
  const { id = '' } = useParams()
  return <Workspace key={id} projectId={id} />
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/p/:id" element={<ProjectRoute />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </>
  )
}
