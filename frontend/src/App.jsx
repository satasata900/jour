import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Overview from './pages/Overview';
import LiveFeed from './pages/LiveFeed';
import Agents from './pages/Agents';
import AddAgent from './pages/AddAgent';
import EditAgent from './pages/EditAgent';
import Sources from './pages/Sources';
import AddSource from './pages/AddSource';
import Summaries from './pages/Summaries';
import Settings from './pages/Settings';
import Users from './pages/Users';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/feed" element={<LiveFeed />} />
                <Route path="/agents" element={<Agents />} />
                <Route path="/agents/add" element={<AddAgent />} />
                <Route path="/agents/:id/edit" element={<EditAgent />} />
                <Route path="/sources" element={<Sources />} />
                <Route path="/sources/add" element={<AddSource />} />
                <Route path="/summaries" element={<Summaries />} />
                <Route path="/users" element={<Users />} />
                <Route path="/settings" element={<Settings />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
