const matchId = new URLSearchParams(window.location.search).get('id') || 1;
const ws = new WebSocket(`ws://${window.location.host}/ws/match/${matchId}`);
const playersLayer = document.getElementById('players-layer');
const ballDot = document.getElementById('ball-dot');
const eventLog = document.getElementById('event-log');

const playerColors = {
    'home': '#00ff88',
    'away': '#ff0055'
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'tracking_update') {
        const payload = data.players || [];
        if (data.ball) {
            payload.push({ id: 'ball', type: 'ball', x: data.ball.x, y: data.ball.y });
        }
        renderTracking(payload);
    } else if (data.type === 'match_event') {
        addEventToLog(data);
    }
};

function renderTracking(payload) {
    // payload: [{id, x, y, team, type}, ...]
    payload.forEach(obj => {
        if (obj.type === 'ball') {
            ballDot.setAttribute('cx', obj.x * 10);
            ballDot.setAttribute('cy', obj.y * 6);
        } else {
            const playerId = obj.player_id || obj.id;
            let dot = document.getElementById(`player-${playerId}`);
            if (!dot) {
                dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                dot.setAttribute('id', `player-${playerId}`);
                dot.setAttribute('r', '8');
                dot.setAttribute('fill', obj.team === 'home' ? playerColors.home : playerColors.away);
                dot.classList.add('player-dot');
                playersLayer.appendChild(dot);

                const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
                text.setAttribute('id', `player-label-${playerId}`);
                text.setAttribute('font-size', '10');
                text.setAttribute('fill', '#fff');
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('dy', '-12');
                text.textContent = obj.label || playerId;
                playersLayer.appendChild(text);
            }
            dot.setAttribute('cx', obj.x * 10);
            dot.setAttribute('cy', obj.y * 6);

            const label = document.getElementById(`player-label-${playerId}`);
            if (label) {
                label.setAttribute('x', obj.x * 10);
                label.setAttribute('y', obj.y * 6);
            }
        }
    });
}

function addEventToLog(event) {
    const div = document.createElement('div');
    div.className = 'event-item';
    const min = event.minute || event.time || '00';
    const type = (event.event_type || event.type || 'EVENT').toUpperCase();
    div.innerHTML = `[${min}'] <strong>${type}</strong> - AI (${event.team})`;
    eventLog.prepend(div);
}
