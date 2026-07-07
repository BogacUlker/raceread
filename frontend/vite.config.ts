import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		// dev-only: proxy API calls to production so offline design work
		// runs against real data without touching the live deployment
		proxy: {
			'/api': {
				target: 'https://raceread.app',
				changeOrigin: true,
			},
		},
	},
});
