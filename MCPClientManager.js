import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

class MCPClientManager {
    constructor() {
        this.client = null;
        this.isConnected = false;
    }

    async initialize() {
        if (this.isConnected) return;

        try {
            console.log('Initializing MCP client...');
            const transport = new StdioClientTransport({
                command: '.venv/bin/python',
                args: ['src/MCPServer.py']
            });

            this.client = new Client(
                {
                    name: "legal-ai-client",
                    version: "1.0.0"
                },
                {
                    capabilities: {}
                }
            );

            await this.client.connect(transport);
            this.isConnected = true;
            console.log('MCP client connected successfully');

            // List available tools for debugging
            try {
                const tools = await this.listTools();
                console.log('Available MCP tools:', tools.tools.map(t => t.name));
            } catch (e) {
                console.warn('Could not list tools immediately:', e);
            }
        } catch (error) {
            console.error('Failed to connect MCP client:', error);
            throw error;
        }
    }

    async callTool(toolRequest) {
        if (!this.isConnected) {
            await this.initialize();
        }

        try {
            console.log('Calling MCP tool:', toolRequest.name, 'with args:', toolRequest.arguments);
            const result = await this.client.callTool({
                name: toolRequest.name,
                arguments: toolRequest.arguments || {}
            });
            console.log('MCP tool result received');
            return result;
        } catch (error) {
            console.error('Tool call failed:', error);
            throw error;
        }
    }

    async listTools() {
        if (!this.isConnected) {
            await this.initialize();
        }

        return await this.client.listTools();
    }

    async disconnect() {
        if (this.isConnected && this.client) {
            await this.client.close();
            this.isConnected = false;
            console.log('MCP client disconnected');
        }
    }
}

export const mcpClient = new MCPClientManager();
