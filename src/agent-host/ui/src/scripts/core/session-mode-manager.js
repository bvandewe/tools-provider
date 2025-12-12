/**
 * Session Mode Manager
 * Manages switching between chat and proactive session modes
 */

import * as bootstrap from 'bootstrap';
import { api } from '../services/api.js';
import { showToast } from '../services/modals.js';
import { setStatus } from './ui-manager.js';
import { getSelectedModelId } from './config-manager.js';

// =============================================================================
// Constants
// =============================================================================

export const SessionMode = {
    CHAT: 'chat',
    THOUGHT: 'thought',
    LEARNING: 'learning',
    VALIDATION: 'validation',
};

export const SessionType = {
    LEARNING: 'learning',
    THOUGHT: 'thought',
    VALIDATION: 'validation',
};

// Learning categories (loaded from question bank)
const DEFAULT_CATEGORIES = [
    { id: 'algebra', name: 'Algebra', description: 'Basic algebraic concepts' },
    { id: 'geometry', name: 'Geometry', description: 'Geometric shapes and reasoning' },
    { id: 'python_basics', name: 'Python Basics', description: 'Fundamental Python programming' },
];

// =============================================================================
// State
// =============================================================================

let state = {
    currentMode: SessionMode.CHAT,
    activeSession: null,
    categories: DEFAULT_CATEGORIES,
    isInitialized: false,
};

// DOM Elements
let elements = {
    modeSelector: null,
    modeDropdown: null,
    currentModeLabel: null,
    chatModeBtn: null,
    learningSubmenu: null,
    categoryList: null,
};

// Callbacks
let callbacks = {
    onModeChange: null,
    onSessionStart: null,
    onSessionEnd: null,
};

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize the session mode manager
 * @param {Object} domElements - DOM element references
 * @param {Object} callbackFunctions - Callback functions
 */
export function initSessionModeManager(domElements, callbackFunctions = {}) {
    elements = { ...elements, ...domElements };
    callbacks = { ...callbacks, ...callbackFunctions };

    // Set up event listeners
    setupEventListeners();

    state.isInitialized = true;
    console.log('[SessionModeManager] Initialized');
}

/**
 * Set up event listeners for mode selection
 */
function setupEventListeners() {
    // Chat mode button (header - legacy)
    elements.chatModeBtn?.addEventListener('click', () => {
        switchToMode(SessionMode.CHAT);
    });

    // Thought session button (header - legacy)
    const thoughtBtn = document.getElementById('thought-mode-btn');
    thoughtBtn?.addEventListener('click', () => {
        startThoughtSession();
    });

    // === Sidebar Mode Selector ===
    // Chat mode button (sidebar)
    const sidebarChatBtn = document.getElementById('sidebar-chat-mode-btn');
    sidebarChatBtn?.addEventListener('click', () => {
        switchToMode(SessionMode.CHAT);
    });

    // Learning session button (sidebar)
    const sidebarLearningBtn = document.getElementById('sidebar-learning-mode-btn');
    sidebarLearningBtn?.addEventListener('click', () => {
        startLearningSession();
    });

    // Thought session button (sidebar)
    const sidebarThoughtBtn = document.getElementById('sidebar-thought-mode-btn');
    sidebarThoughtBtn?.addEventListener('click', () => {
        startThoughtSession();
    });

    // Validation/Evaluation session button (sidebar)
    const sidebarValidationBtn = document.getElementById('sidebar-validation-mode-btn');
    sidebarValidationBtn?.addEventListener('click', () => {
        startValidationSession();
    });
}

/**
 * Render category options in the dropdown(s)
 */
function renderCategories() {
    const categoryHtml = state.categories
        .map(
            cat => `
            <li>
                <button class="dropdown-item" type="button" data-category="${cat.id}">
                    <i class="bi bi-mortarboard me-2"></i>
                    ${cat.name}
                    <small class="text-muted d-block">${cat.description}</small>
                </button>
            </li>
        `
        )
        .join('');

    // Render to header dropdown (legacy)
    if (elements.categoryList) {
        elements.categoryList.innerHTML = categoryHtml;
    }

    // Render to sidebar dropdown
    const sidebarCategoryList = document.getElementById('sidebar-learning-category-list');
    if (sidebarCategoryList) {
        sidebarCategoryList.innerHTML = categoryHtml;
    }
}

// =============================================================================
// Mode Switching
// =============================================================================

/**
 * Switch to a different mode
 * @param {string} mode - The mode to switch to
 */
export function switchToMode(mode) {
    if (state.currentMode === mode) return;

    const previousMode = state.currentMode;
    state.currentMode = mode;

    // Update UI
    updateModeUI();

    // Notify callback
    if (callbacks.onModeChange) {
        callbacks.onModeChange(mode, previousMode);
    }

    console.log(`[SessionModeManager] Switched from ${previousMode} to ${mode}`);
}

/**
 * Update UI to reflect current mode
 */
function updateModeUI() {
    const modeConfig = {
        [SessionMode.CHAT]: { icon: 'bi-chat-dots', label: 'Chat' },
        [SessionMode.LEARNING]: { icon: 'bi-mortarboard', label: 'Learning' },
        [SessionMode.THOUGHT]: { icon: 'bi-lightbulb', label: 'Thought' },
        [SessionMode.VALIDATION]: { icon: 'bi-check-circle', label: 'Validation' },
    };

    const config = modeConfig[state.currentMode] || modeConfig[SessionMode.CHAT];

    // Update the header dropdown toggle label (legacy)
    const icon = elements.modeSelector?.querySelector('.mode-icon');
    const label = elements.modeSelector?.querySelector('.mode-label');

    if (icon) {
        icon.className = `bi ${config.icon} mode-icon`;
    }
    if (label) {
        label.textContent = config.label;
    }

    // Update the sidebar mode icon
    const sidebarModeIcon = document.getElementById('sidebar-mode-icon');
    if (sidebarModeIcon) {
        sidebarModeIcon.className = `bi ${config.icon} sidebar-mode-icon`;
    }

    // Update active state in all dropdowns (header and sidebar)
    document.querySelectorAll('[data-mode]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === state.currentMode);
    });
}

// =============================================================================
// Session Management
// =============================================================================

/**
 * Start a learning session
 */
export async function startLearningSession() {
    try {
        setStatus('connecting', 'Starting learning session...');

        // Get the currently selected model from the UI
        const modelId = getSelectedModelId();

        const session = await api.createSession({
            session_type: SessionType.LEARNING,
            model_id: modelId,
        });

        state.activeSession = session;
        switchToMode(SessionMode.LEARNING);

        showToast('Started learning session', 'success');

        // Notify callback to connect to stream
        if (callbacks.onSessionStart) {
            callbacks.onSessionStart(session);
        }

        console.log('[SessionModeManager] Learning session started:', session);
    } catch (error) {
        console.error('[SessionModeManager] Failed to start learning session:', error);
        showToast(`Failed to start session: ${error.message}`, 'error');
        setStatus('error', 'Session failed');
    }
}

/**
 * Start a thought session
 */
export async function startThoughtSession() {
    try {
        setStatus('connecting', 'Starting session...');

        // Get the currently selected model from the UI
        const modelId = getSelectedModelId();

        const session = await api.createSession({
            session_type: SessionType.THOUGHT,
            model_id: modelId,
        });

        state.activeSession = session;
        switchToMode(SessionMode.THOUGHT);

        showToast('Started thought session', 'success');

        if (callbacks.onSessionStart) {
            callbacks.onSessionStart(session);
        }

        console.log('[SessionModeManager] Thought session started:', session);
    } catch (error) {
        console.error('[SessionModeManager] Failed to start thought session:', error);
        showToast(`Failed to start session: ${error.message}`, 'error');
        setStatus('error', 'Session failed');
    }
}

// =============================================================================
// Exam Selection Modal
// =============================================================================

let examSelectModal = null;
let selectedExamId = null;

/**
 * Initialize the exam selection modal
 */
function initExamSelectModal() {
    const modalEl = document.getElementById('exam-select-modal');
    if (!modalEl) return;

    examSelectModal = new bootstrap.Modal(modalEl);

    // Handle exam selection
    const examList = document.getElementById('exam-list');
    examList?.addEventListener('click', e => {
        const item = e.target.closest('.exam-list-item');
        if (item) {
            // Remove selection from other items
            examList.querySelectorAll('.exam-list-item').forEach(el => {
                el.classList.remove('active');
            });
            // Select this item
            item.classList.add('active');
            selectedExamId = item.dataset.examId;
            // Enable start button
            document.getElementById('start-exam-btn').disabled = false;
        }
    });

    // Handle start button
    document.getElementById('start-exam-btn')?.addEventListener('click', async () => {
        if (selectedExamId) {
            examSelectModal.hide();
            await startValidationSessionWithExam(selectedExamId);
        }
    });

    // Reset state when modal is hidden
    modalEl.addEventListener('hidden.bs.modal', () => {
        selectedExamId = null;
        document.getElementById('start-exam-btn').disabled = true;
        // Clear selection
        document.querySelectorAll('.exam-list-item').forEach(el => {
            el.classList.remove('active');
        });
    });
}

/**
 * Load and display available exams in the modal
 */
async function loadExamsIntoModal() {
    const loadingEl = document.getElementById('exam-list-loading');
    const errorEl = document.getElementById('exam-list-error');
    const emptyEl = document.getElementById('exam-list-empty');
    const listEl = document.getElementById('exam-list');

    // Show loading state
    loadingEl?.classList.remove('d-none');
    errorEl?.classList.add('d-none');
    emptyEl?.classList.add('d-none');
    listEl?.classList.add('d-none');

    try {
        const exams = await api.getExams();

        loadingEl?.classList.add('d-none');

        if (exams.length === 0) {
            emptyEl?.classList.remove('d-none');
            return;
        }

        // Render exam list
        if (listEl) {
            listEl.innerHTML = exams
                .map(
                    exam => `
                <button type="button" class="list-group-item list-group-item-action exam-list-item"
                        data-exam-id="${exam.exam_id}">
                    <div class="d-flex w-100 justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${exam.name}</h6>
                            <p class="mb-1 text-muted small">${exam.description || 'No description'}</p>
                        </div>
                        <span class="badge bg-secondary rounded-pill">${exam.total_items} items</span>
                    </div>
                    ${exam.time_limit_minutes ? `<small class="text-muted"><i class="bi bi-clock me-1"></i>${exam.time_limit_minutes} min</small>` : ''}
                </button>
            `
                )
                .join('');
            listEl.classList.remove('d-none');
        }
    } catch (error) {
        console.error('[SessionModeManager] Failed to load exams:', error);
        loadingEl?.classList.add('d-none');
        if (errorEl) {
            document.getElementById('exam-list-error-msg').textContent = error.message || 'Failed to load exams';
            errorEl.classList.remove('d-none');
        }
    }
}

/**
 * Show the exam selection modal
 */
export async function showExamSelectModal() {
    // Initialize modal if not done yet
    if (!examSelectModal) {
        initExamSelectModal();
    }

    // Load exams and show modal
    examSelectModal?.show();
    await loadExamsIntoModal();
}

/**
 * Start a validation/evaluation session - shows exam selection modal first
 */
export async function startValidationSession() {
    await showExamSelectModal();
}

/**
 * Start a validation session with a specific exam
 * @param {string} examId - The exam ID to use
 */
async function startValidationSessionWithExam(examId) {
    try {
        setStatus('connecting', 'Starting evaluation...');

        // Get the currently selected model from the UI
        const modelId = getSelectedModelId();

        const session = await api.createSession({
            session_type: SessionType.VALIDATION,
            model_id: modelId,
            config: {
                exam_id: examId,
            },
        });

        state.activeSession = session;
        switchToMode(SessionMode.VALIDATION);

        showToast('Started evaluation session', 'success');

        if (callbacks.onSessionStart) {
            callbacks.onSessionStart(session);
        }

        console.log('[SessionModeManager] Validation session started:', session);
    } catch (error) {
        console.error('[SessionModeManager] Failed to start validation session:', error);
        showToast(`Failed to start evaluation: ${error.message}`, 'error');
        setStatus('error', 'Session failed');
    }
}

/**
 * End the current session
 * @param {string} [reason] - Optional reason for ending
 */
export async function endCurrentSession(reason = 'User ended session') {
    if (!state.activeSession) return;

    try {
        await api.terminateSession(state.activeSession.session_id);

        const previousSession = state.activeSession;
        state.activeSession = null;

        switchToMode(SessionMode.CHAT);

        if (callbacks.onSessionEnd) {
            callbacks.onSessionEnd(previousSession, reason);
        }

        showToast('Session ended', 'info');
        console.log('[SessionModeManager] Session ended:', reason);
    } catch (error) {
        console.error('[SessionModeManager] Failed to end session:', error);
        showToast('Failed to end session properly', 'warning');

        // Force local cleanup
        state.activeSession = null;
        switchToMode(SessionMode.CHAT);
    }
}

// =============================================================================
// Getters
// =============================================================================

/**
 * Get current mode
 * @returns {string} Current session mode
 */
export function getCurrentMode() {
    return state.currentMode;
}

/**
 * Get active session
 * @returns {Object|null} Active session or null
 */
export function getActiveSession() {
    return state.activeSession;
}

/**
 * Check if in a proactive session
 * @returns {boolean}
 */
export function isInSession() {
    return state.activeSession !== null;
}

/**
 * Get available categories
 * @returns {Array} List of categories
 */
export function getCategories() {
    return state.categories;
}

// =============================================================================
// Session State Recovery
// =============================================================================

/**
 * Restore session state (e.g., after page refresh)
 * @param {string} sessionId - Session ID to restore
 */
export async function restoreSession(sessionId) {
    try {
        const session = await api.getSession(sessionId);

        if (session.status === 'active' || session.status === 'suspended') {
            state.activeSession = {
                session_id: session.id,
                conversation_id: session.conversation_id,
                status: session.status,
            };

            // Determine mode from session type
            const modeMap = {
                learning: SessionMode.LEARNING,
                thought: SessionMode.THOUGHT,
                validation: SessionMode.VALIDATION,
            };
            switchToMode(modeMap[session.session_type] || SessionMode.CHAT);

            // Check for pending action
            if (session.pending_action) {
                console.log('[SessionModeManager] Session has pending action');
            }

            if (callbacks.onSessionStart) {
                callbacks.onSessionStart(state.activeSession);
            }

            console.log('[SessionModeManager] Session restored:', sessionId);
            return true;
        }
    } catch (error) {
        console.error('[SessionModeManager] Failed to restore session:', error);
    }
    return false;
}
