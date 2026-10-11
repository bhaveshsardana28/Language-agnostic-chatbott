import { API_BASE } from '../config.js';
import { initIcons } from './icons.js';
import { initUI } from './ui.js';
import { initAppearance } from './appearance.js';
import { initShell } from './shell.js';
import { initWelcome } from './welcome.js';
import { initConnection } from './connection.js';

initIcons();
initUI();
initAppearance();
initShell();
initWelcome();
document.getElementById('legacy-link').href = `${API_BASE}/`;
initConnection();
