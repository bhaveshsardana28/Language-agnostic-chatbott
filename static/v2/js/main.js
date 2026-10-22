import { initIcons } from './icons.js';
import { initUI } from './ui.js';
import { initAppearance } from './appearance.js';
import { initShell } from './shell.js';
import { initWelcome } from './welcome.js';
import { initConnection } from './connection.js';
import { initChat } from './chat.js';
import { initDocuments } from './documents.js';
import { initVoiceInput } from './voiceInput.js';

initIcons();
initUI();
initAppearance();
initShell();
initWelcome();
initConnection();
const chatController = initChat();
initDocuments(chatController);
initVoiceInput(chatController);
