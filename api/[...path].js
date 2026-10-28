const excludedRequestHeaders = new Set([
  'connection',
  'content-length',
  'host',
  'transfer-encoding',
]);

const excludedResponseHeaders = new Set([
  'connection',
  'content-encoding',
  'content-length',
  'transfer-encoding',
]);

async function readRequestBody(request) {
  if (request.body === undefined || request.body === null) return undefined;
  if (typeof request.body === 'string' || Buffer.isBuffer(request.body)) return request.body;
  return JSON.stringify(request.body);
}

export default async function handler(request, response) {
  const railwayApiUrl = process.env.RAILWAY_API_URL;
  if (!railwayApiUrl) {
    response.status(503).json({ detail: 'Configure RAILWAY_API_URL nas variáveis da Vercel.' });
    return;
  }

  let upstream;
  let railwayOrigin;
  try {
    railwayOrigin = new URL(railwayApiUrl);
    const requestPath = request.url === '/api/health' ? '/health' : request.url;
    upstream = new URL(requestPath, railwayOrigin);
  } catch {
    response.status(500).json({ detail: 'RAILWAY_API_URL não é uma URL válida.' });
    return;
  }
  if (railwayOrigin.protocol !== 'https:' || upstream.origin !== railwayOrigin.origin) {
    response.status(500).json({ detail: 'RAILWAY_API_URL precisa ser uma origem HTTPS válida.' });
    return;
  }

  const headers = new Headers();
  for (const [name, value] of Object.entries(request.headers)) {
    if (!excludedRequestHeaders.has(name.toLowerCase()) && value !== undefined) {
      headers.set(name, Array.isArray(value) ? value.join(', ') : value);
    }
  }

  try {
    const upstreamResponse = await fetch(upstream, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : await readRequestBody(request),
      redirect: 'manual',
    });
    const responseHeaders = upstreamResponse.headers;
    response.status(upstreamResponse.status);
    responseHeaders.forEach((value, name) => {
      if (!excludedResponseHeaders.has(name.toLowerCase()) && name.toLowerCase() !== 'set-cookie') {
        response.setHeader(name, value);
      }
    });

    const cookies = responseHeaders.getSetCookie?.() || [];
    if (cookies.length) response.setHeader('set-cookie', cookies);
    else {
      const cookie = responseHeaders.get('set-cookie');
      if (cookie) response.setHeader('set-cookie', cookie);
    }

    const body = Buffer.from(await upstreamResponse.arrayBuffer());
    response.end(body);
  } catch (error) {
    console.error('Railway API proxy request failed:', error);
    response.status(502).json({ detail: 'Não foi possível conectar à API hospedada no Railway.' });
  }
}
