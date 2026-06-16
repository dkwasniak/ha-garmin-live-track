// Cloudflare Email Worker — Garmin LiveTrack → Home Assistant

const HA_WEBHOOK_URL = 'https://ha.haosdk.pl/api/webhook/GARMIN_LIVETRACK_WEBHOOK_ID';

export default {
  async email(message, _env, _ctx) {
    const from = message.from;

    if (!from.includes('garmin.com')) {
      message.setReject('Not a Garmin email');
      return;
    }

    const rawEmail = await streamToText(message.raw);

    const sessionUrl = extractLiveTrackUrl(rawEmail);
    if (!sessionUrl) {
      console.log('No LiveTrack URL found in email');
      return;
    }

    const { sessionId, token } = parseSessionUrl(sessionUrl);
    if (!sessionId || !token) {
      console.log('Could not parse sessionId/token from URL:', sessionUrl);
      return;
    }

    console.log(`LiveTrack session: ${sessionId}`);

    // Pobierz aktualną pozycję z Garmin API
    const position = await fetchLiveTrackPosition(sessionId);

    // Wyślij do Home Assistant
    const payload = {
      event: 'livetrack_started',
      session_id: sessionId,
      session_url: sessionUrl,
      token: token,
      position: position,
      timestamp: new Date().toISOString(),
    };

    await sendToHA(payload);
  }
};

function extractLiveTrackUrl(text) {
  // Obsługa quoted-printable (=\n line breaks)
  const decoded = text.replace(/=\r?\n/g, '');
  const match = decoded.match(/https:\/\/livetrack\.garmin\.com\/session\/[a-z0-9\-]+\/token\/[A-Z0-9]+/);
  return match ? match[0] : null;
}

function parseSessionUrl(url) {
  const match = url.match(/\/session\/([a-z0-9\-]+)\/token\/([A-Z0-9]+)/);
  if (!match) return {};
  return { sessionId: match[1], token: match[2] };
}

async function fetchLiveTrackPosition(sessionId) {
  try {
    const url = `https://livetrack.garmin.com/services/session/${sessionId}/trackpoints?requestTime=${Date.now()}`;
    const resp = await fetch(url, {
      headers: {
        'NK': 'NT',
        'Accept': 'application/json',
      }
    });

    if (!resp.ok) {
      console.log(`Garmin API returned ${resp.status}`);
      return null;
    }

    const data = await resp.json();
    const trackpoints = data?.trackPointList?.trackPoints;
    if (!trackpoints?.length) return null;

    const latest = trackpoints[trackpoints.length - 1];
    return {
      lat: latest.lat,
      lon: latest.lon,
      speed: latest.speed,
      altitude: latest.altitude,
      heart_rate: latest.heartRate,
      timestamp: latest.dateTime,
    };
  } catch (e) {
    console.log('Failed to fetch position:', e.message);
    return null;
  }
}

async function sendToHA(payload) {
  const resp = await fetch(HA_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  console.log(`HA webhook: ${resp.status}`);
}

async function streamToText(stream) {
  const reader = stream.getReader();
  const chunks = [];
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  const bytes = new Uint8Array(chunks.reduce((acc, c) => acc + c.length, 0));
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.length;
  }
  return new TextDecoder().decode(bytes);
}
