import { api } from '$lib/api.js';

const SITE = 'https://raceread.app';

export async function GET({ fetch }) {
	let races = [];
	try {
		races = await api('/api/races', fetch);
	} catch (e) {
		// still serve the static pages if the API is down
	}

	const urls = [
		'/',
		'/how',
		'/about',
		'/standings',
		...races.flatMap((r) => [`/race/${r.id}`, `/race/${r.id}/compare`, `/race/${r.id}/broadcast`]),
	];

	const body =
		'<?xml version="1.0" encoding="UTF-8"?>\n' +
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
		urls.map((u) => `\t<url><loc>${SITE}${u}</loc></url>`).join('\n') +
		'\n</urlset>\n';

	return new Response(body, {
		headers: {
			'Content-Type': 'application/xml',
			'Cache-Control': 'public, max-age=3600',
		},
	});
}
