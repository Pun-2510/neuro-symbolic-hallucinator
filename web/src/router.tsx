import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import { UploadPage } from './pages/UploadPage';
import { EssayPage } from './pages/EssayPage';
import { HistoryPage } from './pages/HistoryPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <UploadPage /> },
      { path: 'essays/:id', element: <EssayPage /> },
      { path: 'history', element: <HistoryPage /> },
    ],
  },
]);