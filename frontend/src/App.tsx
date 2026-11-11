import { Navigate, Route, Routes } from 'react-router'

import { AppShell } from './components/AppShell'
import { AlbumDetailPage } from './pages/AlbumDetailPage'
import { AlbumsPage } from './pages/AlbumsPage'
import { BandDetailPage } from './pages/BandDetailPage'
import { BandsPage } from './pages/BandsPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ProducerDetailPage } from './pages/ProducerDetailPage'
import { ProducerGraphPage } from './pages/ProducerGraphPage'
import { ProducersPage } from './pages/ProducersPage'
import { SearchPage } from './pages/SearchPage'

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to="/bands" replace />} />
        <Route path="/bands" element={<BandsPage />} />
        <Route path="/bands/:bandId" element={<BandDetailPage />} />
        <Route path="/albums" element={<AlbumsPage />} />
        <Route path="/albums/:albumId" element={<AlbumDetailPage />} />
        <Route path="/producers" element={<ProducersPage />} />
        <Route path="/producers/:producerId" element={<ProducerDetailPage />} />
        <Route path="/producers/:producerId/graph" element={<ProducerGraphPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App
