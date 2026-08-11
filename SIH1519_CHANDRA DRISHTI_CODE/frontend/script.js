// ---------- Sliders ----------
const sliders = [
    { id: 'conf', el: 'conf-threshold', decimals: 2 },
    { id: 'slope', el: 'slope-threshold', suffix: '°' },
    { id: 'shadow', el: 'shadow-threshold' }
];

sliders.forEach(s => {
    const input = document.getElementById(s.el);
    const valSpan = document.getElementById(`${s.id}-val`);
    input.addEventListener('input', (e) => {
        let val = e.target.value;
        if (s.decimals) val = parseFloat(val).toFixed(s.decimals);
        valSpan.textContent = val + (s.suffix || '');
    });
});

// ---------- File upload (click + drag/drop) ----------
const fileInputs = ['standard', 'dem', 'ortho'];
const filesData = { standard: null, dem: null, ortho: null };

function setFile(type, file) {
    filesData[type] = file;
    const filenameSpan = document.getElementById(`${type}-filename`);
    filenameSpan.textContent = file.name;
    filenameSpan.classList.add('set');
}

fileInputs.forEach(type => {
    const input = document.getElementById(`${type}-image`);
    const dropzone = document.getElementById(`${type}-dropzone`);

    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) setFile(type, e.target.files[0]);
    });

    ['dragenter', 'dragover'].forEach(evt => {
        dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'dragend'].forEach(evt => {
        dropzone.addEventListener(evt, () => dropzone.classList.remove('dragover'));
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) {
            input.files = e.dataTransfer.files;
            setFile(type, file);
        }
    });
});

// ---------- Load Sample Data ----------
document.getElementById('load-sample-btn').addEventListener('click', async () => {
    try {
        const host = window.location.hostname;
        const isLocal = host === 'localhost' || host === '127.0.0.1' || host === '';
        
        // Pointing to the secure local tunnel!
        const PROD_BACKEND_URL = 'https://skirt-edge-upcoming-hearts.trycloudflare.com';
        const baseUrl = isLocal ? `http://${host || '127.0.0.1'}:5000` : PROD_BACKEND_URL;
        const sampleUrl = `${baseUrl}/random_sample`;
        
        const btn = document.getElementById('load-sample-btn');
        const oldText = btn.textContent;
        btn.textContent = 'Loading...';
        btn.disabled = true;

        const response = await fetch(sampleUrl);
        const result = await response.json();
        
        if(result.success) {
            const b64 = result.data.split(',')[1];
            const byteCharacters = atob(b64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], {type: 'image/jpeg'});
            const file = new File([blob], result.filename, {type: 'image/jpeg'});
            
            setFile('standard', file);
            setFile('dem', file);
            setFile('ortho', file);
        } else {
            alert('Failed to load sample data: ' + result.error);
        }
        
        btn.textContent = oldText;
        btn.disabled = false;
    } catch (error) {
        console.error(error);
        alert('Could not connect to backend to load sample.');
        document.getElementById('load-sample-btn').textContent = 'Load Random Sample';
        document.getElementById('load-sample-btn').disabled = false;
    }
});

// ---------- Tabs ----------
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
});

// ---------- Real-Time Clock ----------
function updateClock() {
    const clockEl = document.getElementById('real-time-clock');
    if (clockEl) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
        clockEl.textContent = `${timeStr} UTC`;
    }
}
setInterval(updateClock, 1000);
updateClock();

// ---------- Download Summary Report ----------
document.getElementById('download-report-btn').addEventListener('click', () => {
    const craters = document.getElementById('sum-craters').textContent;
    const slopes = document.getElementById('sum-slopes').textContent;
    const shadows = document.getElementById('sum-shadows').textContent;
    const status = document.getElementById('sum-status').textContent;
    const lzX = document.getElementById('lz-x').textContent;
    const lzY = document.getElementById('lz-y').textContent;
    const lzR = document.getElementById('lz-r').textContent;
    const lzPct = document.getElementById('lz-pct').textContent;

    let report = `=================================\n`;
    report += `   CHANDRA DRISHTI - MISSION REPORT\n`;
    report += `=================================\n\n`;
    report += `Generated: ${new Date().toUTCString()}\n\n`;
    report += `[ SCAN PARAMETERS ]\n`;
    report += `- Grid Resolution:  ${document.getElementById('res-grid').textContent}\n\n`;
    report += `[ HAZARD ANALYSIS ]\n`;
    report += `- Craters Detected: ${craters}\n`;
    report += `- Slope Hazards:    ${slopes}\n`;
    report += `- Shadow Hazards:   ${shadows}\n\n`;
    report += `[ OVERALL STATUS ]\n`;
    report += `>> ${status} <<\n\n`;

    if (status === 'SAFE') {
        report += `[ SAFE LANDING ZONE COORDINATES ]\n`;
        report += `- X Position: ${lzX}\n`;
        report += `- Y Position: ${lzY}\n`;
        report += `- Radius:     ${lzR} px\n`;
        report += `- Confidence: ${lzPct}%\n`;
        
        const roverDist = document.getElementById('lz-rover').textContent;
        if (roverDist !== '--') {
            report += `\n[ SURFACE EXPLORATION PLAN ]\n`;
            report += `- Rover Path to Nearest Crater (Water-Ice): ${roverDist} meters\n`;
        }
        
        const altZones = document.querySelectorAll('.alt-zone-item');
        if (altZones.length > 0 && !document.getElementById('lz-alt-zones').classList.contains('hidden')) {
            report += `\n[ ALTERNATIVE ZONES (CONTINGENCY) ]\n`;
            altZones.forEach((el) => {
                report += `- ${el.innerText.replace(/\n/g, ' ')}\n`;
            });
        }
    } else {
        report += `[ CRITICAL ]\n`;
        report += `NO VIABLE PRIMARY LANDING ZONE DETECTED.\n`;
        report += `OVERALL TERRAIN SAFETY: ${lzPct}%\n`;
        report += `MISSION ABORTED.\n`;
        
        const altZones = document.querySelectorAll('.alt-zone-item');
        if (altZones.length > 0 && !document.getElementById('lz-alt-zones').classList.contains('hidden')) {
            report += `\n[ ALTERNATIVE ZONES (CONTINGENCY) ]\n`;
            altZones.forEach((el) => {
                report += `- ${el.innerText.replace(/\n/g, ' ')}\n`;
            });
        }
    }

    const blob = new Blob([report], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mission_report_${new Date().getTime()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// ---------- File handling ----------
const statusLine = document.getElementById('status-line');
const statusText = document.getElementById('status-text');

function setStatus(text, busy) {
    statusText.textContent = text;
    statusLine.classList.toggle('busy', !!busy);
}

// ---------- Analyze ----------
const analyzeBtn = document.getElementById('analyze-btn');
const btnText = analyzeBtn.querySelector('.btn-text');
const spinner = document.getElementById('loading-spinner');
const resultsSection = document.getElementById('results-section');

analyzeBtn.addEventListener('click', async () => {
    if (!filesData.standard && !filesData.dem && !filesData.ortho) {
        alert('Please upload at least one image file (Standard, DEM, or ORTHO).');
        return;
    }

    analyzeBtn.disabled = true;
    btnText.textContent = 'Analyzing...';
    spinner.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    setStatus('SCANNING', true);

    const formData = new FormData();
    if (filesData.standard) formData.append('standard_image', filesData.standard);
    if (filesData.dem) formData.append('dem_image', filesData.dem);
    if (filesData.ortho) formData.append('ortho_image', filesData.ortho);

    const confVal = document.getElementById('conf-threshold').value;
    const slopeVal = document.getElementById('slope-threshold').value;
    const shadowVal = document.getElementById('shadow-threshold').value;
    const useSr = document.getElementById('sr-toggle').checked;
    formData.append('confidence_threshold', confVal);
    formData.append('slope_threshold', slopeVal);
    formData.append('shadow_threshold', shadowVal);
    formData.append('use_sr', useSr);

    // Update the results page readout with these values
    document.getElementById('res-conf').textContent = parseFloat(confVal).toFixed(2);
    document.getElementById('res-slope').textContent = slopeVal + '°';
    document.getElementById('res-shadow').textContent = shadowVal;
    document.getElementById('res-grid').textContent = useSr ? '1m/px (SR)' : '5m/px (Raw)';

    // Dynamically point to the backend using the local tunnel
    const host = window.location.hostname;
    const isLocal = host === 'localhost' || host === '127.0.0.1' || host === '';
    const PROD_BACKEND_URL = 'https://skirt-edge-upcoming-hearts.trycloudflare.com';
    const baseUrl = isLocal ? `http://${host || '127.0.0.1'}:5000` : PROD_BACKEND_URL;
    const backendUrl = `${baseUrl}/analyze`;

    try {
        const response = await fetch(backendUrl, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            const data = result.data;

            if (data.master_map) document.getElementById('master-img').src = data.master_map;
            if (data.object_detection) document.getElementById('objects-img').src = data.object_detection;
            if (data.slope_map) document.getElementById('slopes-img').src = data.slope_map;
            if (data.shadow_map) document.getElementById('shadows-img').src = data.shadow_map;

            // Always show the panel
            document.getElementById('mission-control').classList.remove('hidden');

            if (data.landing_zone) {
                document.getElementById('lz-pct').textContent = data.landing_zone.safe_percentage;
                
                const altContainer = document.getElementById('alt-zones-container');
                const altWrapper = document.getElementById('lz-alt-zones');
                altContainer.innerHTML = '';
                
                if (data.landing_zone.alt_zones && data.landing_zone.alt_zones.length > 0) {
                    altWrapper.classList.remove('hidden');
                    data.landing_zone.alt_zones.forEach((alt, idx) => {
                        altContainer.innerHTML += `
                            <div class="alt-zone-item">
                                <div><span class="label">ALT ${idx + 1}:</span> X: ${alt.x}, Y: ${alt.y}</div>
                                <div><span class="label">RAD:</span> ${alt.radius} px</div>
                            </div>
                        `;
                    });
                } else if (data.landing_zone.safe_percentage < 75.0) {
                    // Safety is below 75%, but no alternative zones could be found
                    altWrapper.classList.remove('hidden');
                    altContainer.innerHTML = `
                        <div class="alt-zone-item" style="color: var(--red);">
                            <div>No backup zones exist. Terrain is completely hazardous.</div>
                        </div>
                    `;
                } else {
                    altWrapper.classList.add('hidden');
                }

                if (data.landing_zone.radius) {
                    // SUCCESS STATE
                    document.getElementById('lz-success').classList.remove('hidden');
                    document.getElementById('lz-failure').classList.add('hidden');
                    document.getElementById('lz-icon').textContent = '⊕';
                    document.getElementById('lz-title').textContent = 'Safe Landing Zone';
                    document.getElementById('lz-icon').style.color = 'var(--green)';
                    document.getElementById('lz-title').style.color = 'var(--green)';
                    document.getElementById('mission-control').style.boxShadow = '';
                    document.getElementById('mission-control').style.borderColor = '';

                    document.getElementById('lz-x').textContent = data.landing_zone.x;
                    document.getElementById('lz-y').textContent = data.landing_zone.y;
                    document.getElementById('lz-r').textContent = data.landing_zone.radius;
                    
                    if (data.landing_zone.rover_path) {
                        document.getElementById('rover-path-container').style.display = 'block';
                        document.getElementById('lz-rover').textContent = data.landing_zone.rover_path.distance_meters;
                    } else {
                        document.getElementById('rover-path-container').style.display = 'none';
                    }
                    
                    document.getElementById('sum-status').textContent = 'SAFE';
                    document.getElementById('sum-status').style.color = 'var(--green)';
                } else {
                    // FAILURE STATE
                    document.getElementById('lz-success').classList.add('hidden');
                    document.getElementById('lz-failure').classList.remove('hidden');
                    document.getElementById('lz-icon').textContent = '⚠';
                    document.getElementById('lz-title').textContent = 'MISSION ABORT';
                    document.getElementById('lz-icon').style.color = 'var(--red)';
                    document.getElementById('lz-title').style.color = 'var(--red)';
                    document.getElementById('mission-control').style.boxShadow = '0 0 30px rgba(255, 42, 95, 0.3)';
                    document.getElementById('mission-control').style.borderColor = 'rgba(255, 42, 95, 0.4)';
                    
                    document.getElementById('sum-status').textContent = 'ABORT';
                    document.getElementById('sum-status').style.color = 'var(--red)';
                }
            }

            document.getElementById('sum-craters').textContent = data.num_hazards !== undefined ? data.num_hazards : '0';
            document.getElementById('sum-slopes').textContent = data.slope_map ? 'Detected' : 'Skipped';
            document.getElementById('sum-shadows').textContent = data.shadow_map ? 'Detected' : 'Skipped';

            resultsSection.classList.remove('hidden');
            
            // Hide the input panels to create a "new page" feel
            document.getElementById('panel-input').classList.add('hidden');
            document.getElementById('panel-params').classList.add('hidden');
            document.querySelector('.hero').classList.add('hidden');
            
            window.scrollTo({ top: 0, behavior: 'smooth' });
            setStatus('SCAN COMPLETE', false);
        } else {
            alert('Error during analysis: ' + result.error);
            setStatus('SCAN FAILED', false);
        }
    } catch (error) {
        console.error(error);
        alert('Failed to connect to the backend server. Is it running?');
        setStatus('BACKEND OFFLINE', false);
    } finally {
        analyzeBtn.disabled = false;
        btnText.textContent = '▸ Initiate Scan';
        spinner.classList.add('hidden');
    }
});

// ---------- Reset / New Scan ----------
document.getElementById('new-scan-btn').addEventListener('click', () => {
    // Hide results
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('mission-control').classList.add('hidden');
    
    // Show inputs again
    document.getElementById('panel-input').classList.remove('hidden');
    document.getElementById('panel-params').classList.remove('hidden');
    document.querySelector('.hero').classList.remove('hidden');
    
    // Reset status
    setStatus('SYSTEM READY', false);
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
});