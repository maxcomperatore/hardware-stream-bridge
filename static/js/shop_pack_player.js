/** Full-length shop pack audition player (Web Audio). */

(function () {
    const DEMO_BPM = 96;
    const BEAT_SEC = 60 / DEMO_BPM;
    const DEMO_BEATS = 36;
    const DEMO_MS = Math.round(DEMO_BEATS * BEAT_SEC * 1000);

    const CHORD_LOOP = [
        { name: 'Am', notes: [45, 57, 60, 64] },
        { name: 'F', notes: [41, 53, 57, 60] },
        { name: 'C', notes: [48, 55, 60, 64] },
        { name: 'G', notes: [43, 55, 59, 62] },
    ];

    const MELODY = [76, 79, 81, 79, 76, 74, 72, 74, 76, 79, 81, 84, 81, 79, 76, 72];

    function midiToFreq(midi) {
        return 440 * Math.pow(2, (midi - 69) / 12);
    }

    function buildDemoEvents() {
        const events = [];
        const chordBeats = 2;
        const totalChords = Math.floor(DEMO_BEATS / chordBeats);

        for (let i = 0; i < totalChords; i += 1) {
            const chord = CHORD_LOOP[i % CHORD_LOOP.length];
            const at = i * chordBeats;
            chord.notes.forEach((midi) => {
                events.push({ midi, at, dur: chordBeats * 1.85, vel: 0.55, role: 'chord' });
            });
            events.push({ midi: chord.notes[0] - 12, at, dur: chordBeats * 1.9, vel: 0.75, role: 'bass' });
        }

        MELODY.forEach((midi, i) => {
            const at = 4 + i * 2;
            if (at + 1.6 < DEMO_BEATS) {
                events.push({ midi, at, dur: 1.45, vel: 0.5, role: 'lead' });
            }
        });

        return events;
    }

    const DEMO_EVENTS = buildDemoEvents();

    let audioCtx = null;
    let activeSession = null;

    function initAudioContext() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        return audioCtx;
    }

    function setButtonPlaying(btn, playing) {
        const label = btn.querySelector('.shop-play-label');
        if (playing) {
            btn.classList.add('playing');
            if (label) label.textContent = 'Pause demo';
            btn.setAttribute('aria-label', `Pause demo for ${btn.dataset.packName || 'pack'}`);
        } else {
            btn.classList.remove('playing');
            if (label) label.textContent = 'Play demo';
            btn.setAttribute('aria-label', `Play demo for ${btn.dataset.packName || 'pack'}`);
        }
    }

    function stopAudition() {
        if (!activeSession) return;
        if (activeSession.timeout) clearTimeout(activeSession.timeout);
        activeSession.nodes.forEach((node) => {
            try {
                if (typeof node.stop === 'function') node.stop(0);
                if (typeof node.disconnect === 'function') node.disconnect();
            } catch (e) { /* already stopped */ }
        });
        setButtonPlaying(activeSession.btn, false);
        activeSession = null;
    }

    function connectChain(nodes, destination) {
        for (let i = 0; i < nodes.length - 1; i += 1) {
            nodes[i].connect(nodes[i + 1]);
        }
        nodes[nodes.length - 1].connect(destination);
        return nodes;
    }

    function playM1Voice(ctx, freq, start, duration, velocity, dest, nodes) {
        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const gain = ctx.createGain();
        const filter = ctx.createBiquadFilter();
        osc1.type = 'sawtooth';
        osc2.type = 'sawtooth';
        osc1.frequency.value = freq;
        osc2.frequency.value = freq * 1.007;
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(280, start);
        filter.frequency.exponentialRampToValueAtTime(4200, start + 0.08);
        filter.frequency.exponentialRampToValueAtTime(900, start + duration * 0.7);
        filter.Q.value = 0.9;
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.linearRampToValueAtTime(velocity * 0.11, start + 0.04);
        gain.gain.setValueAtTime(velocity * 0.09, start + duration * 0.55);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
        osc1.connect(filter);
        osc2.connect(filter);
        filter.connect(gain);
        gain.connect(dest);
        osc1.start(start);
        osc2.start(start);
        osc1.stop(start + duration + 0.05);
        osc2.stop(start + duration + 0.05);
        nodes.push(osc1, osc2, filter, gain);
    }

    function playDx7Voice(ctx, freq, start, duration, velocity, dest, nodes) {
        const carrier = ctx.createOscillator();
        const mod = ctx.createOscillator();
        const modGain = ctx.createGain();
        const filter = ctx.createBiquadFilter();
        const gain = ctx.createGain();
        carrier.type = 'sine';
        mod.type = 'sine';
        carrier.frequency.value = freq;
        mod.frequency.value = freq * 3.01;
        modGain.gain.setValueAtTime(freq * 2.2, start);
        modGain.gain.exponentialRampToValueAtTime(freq * 0.4, start + duration * 0.8);
        mod.connect(modGain);
        modGain.connect(carrier.frequency);
        filter.type = 'lowpass';
        filter.frequency.value = 6000;
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.linearRampToValueAtTime(velocity * 0.12, start + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
        carrier.connect(filter);
        filter.connect(gain);
        gain.connect(dest);
        carrier.start(start);
        mod.start(start);
        carrier.stop(start + duration + 0.05);
        mod.stop(start + duration + 0.05);
        nodes.push(carrier, mod, modGain, filter, gain);
    }

    function playJunoVoice(ctx, freq, start, duration, velocity, dest, nodes, role) {
        const osc = ctx.createOscillator();
        const chorus = ctx.createOscillator();
        const gain = ctx.createGain();
        const chorusGain = ctx.createGain();
        const filter = ctx.createBiquadFilter();
        const isBass = role === 'bass';
        osc.type = isBass ? 'sawtooth' : 'square';
        chorus.type = isBass ? 'sawtooth' : 'square';
        osc.frequency.value = freq;
        chorus.frequency.value = freq * 1.005;
        chorusGain.gain.value = isBass ? 0.35 : 0.55;
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(isBass ? 420 : 1200, start);
        filter.frequency.linearRampToValueAtTime(isBass ? 900 : 3200, start + 0.12);
        filter.frequency.exponentialRampToValueAtTime(isBass ? 300 : 800, start + duration);
        filter.Q.value = isBass ? 1.2 : 2.4;
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.linearRampToValueAtTime(velocity * (isBass ? 0.13 : 0.09), start + 0.03);
        gain.gain.setValueAtTime(velocity * (isBass ? 0.11 : 0.07), start + duration * 0.5);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
        osc.connect(filter);
        chorus.connect(chorusGain);
        chorusGain.connect(filter);
        filter.connect(gain);
        gain.connect(dest);
        osc.start(start);
        chorus.start(start);
        osc.stop(start + duration + 0.05);
        chorus.stop(start + duration + 0.05);
        nodes.push(osc, chorus, chorusGain, filter, gain);
    }

    function scheduleEvent(packId, event, ctx, startTime, master, nodes) {
        const freq = midiToFreq(event.midi);
        const when = startTime + event.at * BEAT_SEC;
        const duration = event.dur * BEAT_SEC;
        if (packId === 'm1_matrix') {
            playM1Voice(ctx, freq, when, duration, event.vel, master, nodes);
        } else if (packId === 'dx7_retro') {
            playDx7Voice(ctx, freq, when, duration, event.vel, master, nodes);
        } else {
            playJunoVoice(ctx, freq, when, duration, event.vel, master, nodes, event.role);
        }
    }

    function startAudition(packId, btn) {
        const ctx = initAudioContext();
        if (!ctx) return;

        const master = ctx.createGain();
        master.gain.value = 0.85;
        master.connect(ctx.destination);

        const nodes = [master];
        const now = ctx.currentTime + 0.05;

        DEMO_EVENTS.forEach((event) => {
            scheduleEvent(packId, event, ctx, now, master, nodes);
        });

        setButtonPlaying(btn, true);
        activeSession = {
            packId,
            btn,
            nodes,
            timeout: setTimeout(stopAudition, DEMO_MS + 120),
        };
    }

    function toggleAudition(packId, btn) {
        if (!packId) return;
        if (activeSession?.packId === packId && activeSession.btn === btn) {
            stopAudition();
            return;
        }
        stopAudition();
        startAudition(packId, btn);
    }

    document.querySelectorAll('.shop-play-btn').forEach((btn) => {
        btn.addEventListener('click', () => toggleAudition(btn.dataset.packId, btn));
    });
})();
