/**
 * App — 路由入口
 * AI Guitar Tab 前端
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Result from './pages/Result';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/result/:taskId" element={<Result />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
