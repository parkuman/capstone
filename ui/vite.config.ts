import { sveltekit } from '@sveltejs/kit/vite';
import { Server } from "socket.io";
import handleSocket from "./server/handleSocket";
import type { PluginOption, UserConfig } from 'vite';

const socketioServer: PluginOption = {
  name: "socketioServer",
  configureServer(server) {
    if (server.httpServer) {
      const io = new Server(server.httpServer);
			handleSocket(io);
    }
  },
};

const config: UserConfig = {
	plugins: [sveltekit(), socketioServer],
	server: {
		port: 3000,
	},
	preview: {
		port: 3000,
	}
};

export default config;
