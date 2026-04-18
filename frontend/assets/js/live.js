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
    
    if (data.type === 'tracking') {
        renderTracking(data.payload);
    } else if (data.type === 'event') {
        addEventToLog(data.payload);
    }
};

function renderTracking(payload) {
    // payload: [{id, x, y, team, type}, ...]
    payload.forEach(obj => {
        if (obj.type === 'ball') {
            ballDot.setAttribute('cx', obj.x);
            ballDot.setAttribute('cy', obj.y);
        } else {
            let dot = document.getElementById(`player-${obj.id}`);
            if (!dot) {
                dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                dot.setAttribute('id', `player-${obj.id}`);
                dot.setAttribute('r', '8');
                dot.setAttribute('fill', obj.team === 'home' ? playerColors.home : playerColors.away);
                dot.classList.add('player-dot');
                playersLayer.appendChild(dot);

                const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
                text.setAttribute('id', `player-label-${obj.id}`);
                text.setAttribute('font-size', '10');
                text.setAttribute('fill', '#fff');
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('dy', '-12');
                text.textContent = obj.label || obj.id;
                playersLayer.appendChild(text);
            }
            dot.setAttribute('cx', obj.x);
            dot.setAttribute('cy', obj.y);

            const label = document.getElementById(`player-label-${obj.id}`);
            if (label) {
                label.setAttribute('x', obj.x);
                label.setAttribute('y', obj.y);
            }
        }
    });
}

function addEventToLog(event) {
    const div = document.createElement('div');
    div.className = 'event-item';
    div.innerHTML = `[${event.time}'] <strong>${event.type.toUpperCase()}</strong> - ${event.player} (${event.team})`;
    eventLog.prepend(div);
}
