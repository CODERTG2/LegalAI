import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { mcpClient } from './MCPClientManager.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Initialize MCP client on server start
mcpClient.initialize().catch(console.error);

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.post('/api/mcp', async (req, res) => {
    try {
        console.log('Received MCP request:', req.body);
        const result = await mcpClient.callTool(req.body);
        res.json(result);
    } catch (error) {
        console.error('MCP tool call error:', error);
        res.status(500).json({
            error: error.message,
            details: error.toString()
        });
    }
});

const server = app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});

async function shutdown() {
    console.log('Shutting down server...');
    server.close(() => {
        console.log('HTTP server closed');
    });
    await mcpClient.disconnect();
    process.exit(0);
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
