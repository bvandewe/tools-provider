/**
 * Control Plane Event Handlers (Class-based)
 *
 * Handles WebSocket protocol control-level messages using class-based architecture
 * with dependency injection via imported singletons.
 *
 * Control events include:
 * - Conversation state (config, lifecycle, deadline)
 * - Item context and scoring
 * - Widget state and rendering
 * - Navigation requests
 * - Flow control (chat input, progress)
 * - Panel header updates
 *
 * These map to backend events from: application/protocol/control.py
 *
 * @module handlers/ControlHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { widgetRenderer } from '../renderers/WidgetRenderer.js';
import { submitWidgetResponse } from '../protocol/websocket-client.js';
import { scrollToBottom } from '../utils/dom.js';

// Import managers (class-based singletons)
import { chatManager } from '../managers/ChatManager.js';
import { panelHeaderManager } from '../managers/PanelHeaderManager.js';
import { messageRenderer } from '../renderers/MessageRenderer.js';
import { showToast } from '../services/modals.js';

/**
 * @class ControlHandlers
 * @description Handles all WebSocket control plane events
 */
export class ControlHandlers {
    /**
     * Create ControlHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        // Runtime state
        /** @type {Object|null} Current conversation config */
        this.conversationConfig = null;

        /** @type {Object|null} Enabled features */
        this.enabledFeatures = null;

        /** @type {Date|null} Conversation deadline */
        this.deadline = null;

        /** @type {Object|null} Current item context */
        this.currentItem = null;

        /** @type {boolean} Whether the welcome start button has been shown for current item */
        this._welcomeStartShown = false;

        /** @type {boolean} Whether we're waiting for user to click Start */
        this._welcomePending = false;

        /** @type {Array} Queue of widget render payloads while welcome is pending */
        this._pendingWidgets = [];

        // Bind all handlers
        this._handleConversationConfig = this._handleConversationConfig.bind(this);
        this._handleConversationDisplay = this._handleConversationDisplay.bind(this);
        this._handleConversationDeadline = this._handleConversationDeadline.bind(this);
        this._handleConversationStarted = this._handleConversationStarted.bind(this);
        this._handleConversationPaused = this._handleConversationPaused.bind(this);
        this._handleConversationResumed = this._handleConversationResumed.bind(this);
        this._handleConversationCompleted = this._handleConversationCompleted.bind(this);
        this._handleConversationTerminated = this._handleConversationTerminated.bind(this);
        this._handleItemContext = this._handleItemContext.bind(this);
        this._handleItemScore = this._handleItemScore.bind(this);
        this._handleItemTimeout = this._handleItemTimeout.bind(this);
        this._handleItemExpired = this._handleItemExpired.bind(this);
        this._handleWidgetState = this._handleWidgetState.bind(this);
        this._handleWidgetRender = this._handleWidgetRender.bind(this);
        this._handleWidgetDismiss = this._handleWidgetDismiss.bind(this);
        this._handleWidgetUpdate = this._handleWidgetUpdate.bind(this);
        this._handleNavigationRequest = this._handleNavigationRequest.bind(this);
        this._handleNavigationAck = this._handleNavigationAck.bind(this);
        this._handleNavigationDenied = this._handleNavigationDenied.bind(this);
        this._handleFlowChatInput = this._handleFlowChatInput.bind(this);
        this._handleFlowProgress = this._handleFlowProgress.bind(this);
        this._handlePanelHeader = this._handlePanelHeader.bind(this);
        this._handleWelcomeMessageComplete = this._handleWelcomeMessageComplete.bind(this);
    }

    /**
     * Initialize handlers and subscribe to events
     * @returns {void}
     */
    init() {
        if (this._initialized) {
            console.warn('[ControlHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;
        console.log('[ControlHandlers] Initialized');
    }

    /**
     * Subscribe to EventBus events
     * @private
     */
    _subscribeToEvents() {
        // Conversation handlers
        this._unsubscribers.push(
            eventBus.on(Events.CONTROL_CONVERSATION_CONFIG, this._handleConversationConfig),
            eventBus.on(Events.CONTROL_CONVERSATION_DISPLAY, this._handleConversationDisplay),
            eventBus.on(Events.CONTROL_CONVERSATION_DEADLINE, this._handleConversationDeadline),
            eventBus.on(Events.CONTROL_CONVERSATION_STARTED, this._handleConversationStarted),
            eventBus.on(Events.CONTROL_CONVERSATION_PAUSED, this._handleConversationPaused),
            eventBus.on(Events.CONTROL_CONVERSATION_RESUMED, this._handleConversationResumed),
            eventBus.on(Events.CONTROL_CONVERSATION_COMPLETED, this._handleConversationCompleted),
            eventBus.on(Events.CONTROL_CONVERSATION_TERMINATED, this._handleConversationTerminated)
        );

        // Item handlers
        this._unsubscribers.push(
            eventBus.on(Events.CONTROL_ITEM_CONTEXT, this._handleItemContext),
            eventBus.on(Events.CONTROL_ITEM_SCORE, this._handleItemScore),
            eventBus.on(Events.CONTROL_ITEM_TIMEOUT, this._handleItemTimeout),
            eventBus.on(Events.CONTROL_ITEM_EXPIRED, this._handleItemExpired)
        );

        // Widget handlers
        this._unsubscribers.push(
            eventBus.on(Events.CONTROL_WIDGET_STATE, this._handleWidgetState),
            eventBus.on(Events.CONTROL_WIDGET_RENDER, this._handleWidgetRender),
            eventBus.on(Events.CONTROL_WIDGET_DISMISS, this._handleWidgetDismiss),
            eventBus.on(Events.CONTROL_WIDGET_UPDATE, this._handleWidgetUpdate)
        );

        // Navigation handlers
        this._unsubscribers.push(
            eventBus.on(Events.CONTROL_NAVIGATION_REQUEST, this._handleNavigationRequest),
            eventBus.on(Events.CONTROL_NAVIGATION_ACK, this._handleNavigationAck),
            eventBus.on(Events.CONTROL_NAVIGATION_DENIED, this._handleNavigationDenied)
        );

        // Flow control handlers
        this._unsubscribers.push(eventBus.on(Events.CONTROL_FLOW_CHAT_INPUT, this._handleFlowChatInput), eventBus.on(Events.CONTROL_FLOW_PROGRESS, this._handleFlowProgress));

        // Panel header handlers
        this._unsubscribers.push(eventBus.on(Events.CONTROL_PANEL_HEADER, this._handlePanelHeader));

        // Welcome message complete handler - for showing Start button on first item
        this._unsubscribers.push(eventBus.on(Events.MESSAGE_COMPLETE, this._handleWelcomeMessageComplete));
    }

    // =========================================================================
    // CONVERSATION HANDLERS
    // =========================================================================

    /**
     * Handler for control.conversation.config
     * Server sends conversation configuration/settings
     * @private
     */
    _handleConversationConfig(payload) {
        console.log('[ControlHandlers] Conversation config:', payload);

        this.conversationConfig = payload;

        if (payload.mode === 'assessment') {
            // Assessment mode UI adjustments would go here
        }

        if (payload.features) {
            this.enabledFeatures = payload.features;
        }
    }

    /**
     * Handler for control.conversation.display
     * Server requests display state change
     * @private
     */
    _handleConversationDisplay(payload) {
        console.log('[ControlHandlers] Conversation display:', payload);
        // Display state changes would go here
    }

    /**
     * Handler for control.conversation.deadline
     * Server updates conversation deadline (for timed assessments)
     * @private
     */
    _handleConversationDeadline(payload) {
        console.log('[ControlHandlers] Conversation deadline:', payload);
        this.deadline = new Date(payload.deadline);
        // Start deadline timer would go here
    }

    /**
     * Handler for control.conversation.started
     * @private
     */
    _handleConversationStarted(payload) {
        console.log('[ControlHandlers] Conversation started:', payload);

        eventBus.emit(Events.CONVERSATION_UPDATED, {
            id: payload.conversationId,
            status: 'active',
        });
    }

    /**
     * Handler for control.conversation.paused
     * @private
     */
    _handleConversationPaused(payload) {
        console.log('[ControlHandlers] Conversation paused:', payload);

        chatManager.disableInput();

        if (payload.reason) {
            showToast(`Paused: ${payload.reason}`, 'info');
        }
    }

    /**
     * Handler for control.conversation.resumed
     * @private
     */
    _handleConversationResumed(payload) {
        console.log('[ControlHandlers] Conversation resumed:', payload);
        // Note: Chat input state is controlled by backend via control.flow.chatInput
    }

    /**
     * Handler for control.conversation.completed
     * @private
     */
    _handleConversationCompleted(payload) {
        console.log('[ControlHandlers] Conversation completed:', payload);

        chatManager.disableInput();

        eventBus.emit(Events.TEMPLATE_COMPLETE, payload);
    }

    /**
     * Handler for control.conversation.terminated
     * @private
     */
    _handleConversationTerminated(payload) {
        console.log('[ControlHandlers] Conversation terminated:', payload);

        chatManager.disableInput();

        showToast(`Conversation ended: ${payload.reason}`, 'warning');
    }

    // =========================================================================
    // ITEM HANDLERS
    // =========================================================================

    /**
     * Handler for control.item.context
     * Server sends context for a template item
     * @private
     */
    _handleItemContext(payload) {
        console.log('[ControlHandlers] Item context received:', {
            itemId: payload.itemId,
            itemIndex: payload.itemIndex,
            requireUserConfirmation: payload.requireUserConfirmation,
            confirmationButtonText: payload.confirmationButtonText,
            enableChatInput: payload.enableChatInput,
        });

        // Clear widgets from previous item
        widgetRenderer.clearWidgets();

        // For first item (itemIndex === 0), set welcome pending - user must click Start
        // For subsequent items, clear previous messages and proceed normally
        if (payload.itemIndex === 0) {
            this._welcomePending = true;
            this._pendingWidgets = [];
            console.log('[ControlHandlers] Welcome phase started - widgets will be queued');
        } else {
            this._welcomePending = false;
            messageRenderer.clearMessages();
        }

        panelHeaderManager.updateProgress(payload.itemIndex, payload.totalItems);

        if (payload.enableChatInput !== undefined) {
            if (payload.enableChatInput) {
                chatManager.enableInput();
            } else {
                chatManager.disableInput();
            }
        }

        stateManager.set(StateKeys.CURRENT_ITEM_CONTEXT, payload);
        this.currentItem = payload;
    }

    /**
     * Handler for control.item.score
     * @private
     */
    _handleItemScore(payload) {
        console.log('[ControlHandlers] Item score:', payload);

        if (payload.showToUser) {
            // Show score would go here
        }

        eventBus.emit('item:scored', payload);
    }

    /**
     * Handler for control.item.timeout
     * @private
     */
    _handleItemTimeout(payload) {
        console.log('[ControlHandlers] Item timeout warning:', payload);

        if (payload.remainingSeconds > 10) {
            showToast(`${payload.remainingSeconds} seconds remaining`, 'warning');
        }
    }

    /**
     * Handler for control.item.expired
     * @private
     */
    _handleItemExpired(payload) {
        console.log('[ControlHandlers] Item expired:', payload);
        showToast('Time expired for this item', 'warning');
    }

    // =========================================================================
    // WIDGET HANDLERS
    // =========================================================================

    /**
     * Handler for control.widget.state
     * @private
     */
    _handleWidgetState(payload) {
        console.log('[ControlHandlers] Widget state:', payload);
        // Widget state update would go here
    }

    /**
     * Handler for control.widget.render
     * @private
     */
    _handleWidgetRender(payload) {
        console.log('[ControlHandlers] Widget render:', {
            widgetId: payload.widgetId || payload.id,
            widgetType: payload.widgetType,
            welcomePending: this._welcomePending,
            currentItemIndex: this.currentItem?.itemIndex,
        });

        // If welcome is pending, queue the widget instead of rendering
        if (this._welcomePending) {
            console.log('[ControlHandlers] Welcome pending - queuing widget:', payload.widgetId || payload.id);
            this._pendingWidgets.push(payload);
            return;
        }

        console.log('[ControlHandlers] Welcome NOT pending - rendering widget immediately:', payload.widgetId || payload.id);
        eventBus.emit(Events.WIDGET_RENDERED, payload);
    }

    /**
     * Handler for control.widget.dismiss
     * @private
     */
    _handleWidgetDismiss(payload) {
        console.log('[ControlHandlers] Widget dismiss:', payload);
        // Widget dismissal would go here
    }

    /**
     * Handler for control.widget.update
     * @private
     */
    _handleWidgetUpdate(payload) {
        console.log('[ControlHandlers] Widget update:', payload);
        // Widget update would go here
    }

    // =========================================================================
    // NAVIGATION HANDLERS
    // =========================================================================

    /**
     * Handler for control.navigation.request
     * @private
     */
    _handleNavigationRequest(payload) {
        console.log('[ControlHandlers] Navigation request:', payload);
        // Navigation would go here
    }

    /**
     * Handler for control.navigation.ack
     * @private
     */
    _handleNavigationAck(payload) {
        console.log('[ControlHandlers] Navigation ack:', payload);
        // Usually no action needed
    }

    /**
     * Handler for control.navigation.denied
     * @private
     */
    _handleNavigationDenied(payload) {
        console.log('[ControlHandlers] Navigation denied:', payload);
        showToast(payload.reason, 'warning');
    }

    // =========================================================================
    // FLOW CONTROL HANDLERS
    // =========================================================================

    /**
     * Handler for control.flow.chatInput
     * Server controls chat input state
     * @private
     */
    _handleFlowChatInput(payload) {
        console.log('[ControlHandlers] Flow chat input:', payload);

        if (payload.hideAll) {
            chatManager.hideAllChatInputButtons(payload.placeholder);
        } else if (payload.enabled) {
            chatManager.showAllChatInputButtons();
            chatManager.enableInput();
        } else {
            chatManager.hideAllChatInputButtons(payload.placeholder);
        }
    }

    /**
     * Handler for control.flow.progress
     * @private
     */
    _handleFlowProgress(payload) {
        console.log('[ControlHandlers] Flow progress:', payload);

        panelHeaderManager.updateProgress(payload.current, payload.total, payload.label);

        eventBus.emit(Events.TEMPLATE_PROGRESS, payload);
    }

    // =========================================================================
    // PANEL HEADER HANDLERS
    // =========================================================================

    /**
     * Handler for control.panel.header
     * Server sends panel header state update (progress, title, score)
     * @private
     */
    _handlePanelHeader(payload) {
        console.log('[ControlHandlers] Panel header:', payload);

        if (payload.progress) {
            panelHeaderManager.updateProgress(payload.progress.current, payload.progress.total, payload.progress.label);
        }

        if (payload.title) {
            panelHeaderManager.updatePanelTitle(payload.title.text, payload.title.visible);
        }

        if (payload.score) {
            panelHeaderManager.updatePanelScore(payload.score.current, payload.score.max, payload.score.label, payload.score.visible);
        }

        eventBus.emit(Events.TEMPLATE_PROGRESS, payload);
    }

    // =========================================================================
    // WELCOME MESSAGE HANDLERS
    // =========================================================================

    /**
     * Handler for MESSAGE_COMPLETE when on first item (itemIndex === 0)
     * Renders a "Start" button to allow user to acknowledge welcome and proceed
     * @private
     */
    _handleWelcomeMessageComplete(payload) {
        // Only show Start button for first item (itemIndex === 0) and only once
        if (!this.currentItem || this.currentItem.itemIndex !== 0 || this._welcomeStartShown) {
            return;
        }

        console.log('[ControlHandlers] Welcome message complete, showing Start button');
        this._welcomeStartShown = true;

        // Create and render the Start button
        this._renderStartButton();
    }

    /**
     * Render the Start button for welcome message acknowledgment
     * @private
     */
    _renderStartButton() {
        const messagesContainer = document.getElementById('messages-container');
        if (!messagesContainer) {
            console.warn('[ControlHandlers] Messages container not found');
            return;
        }

        // Create the Start button
        const buttonContainer = document.createElement('div');
        buttonContainer.id = 'welcome-start-button';
        buttonContainer.className = 'd-flex justify-content-center my-3';

        const startButton = document.createElement('button');
        startButton.className = 'btn btn-primary btn-lg px-5';
        startButton.textContent = 'Start';
        startButton.setAttribute('type', 'button');

        startButton.addEventListener('click', () => this._handleStartButtonClick());

        buttonContainer.appendChild(startButton);
        messagesContainer.appendChild(buttonContainer);
        scrollToBottom(messagesContainer);
    }

    /**
     * Handle Start button click - clear messages and render queued widgets
     * @private
     */
    _handleStartButtonClick() {
        console.log('[ControlHandlers] Start button clicked');

        // Remove the Start button
        const startButtonContainer = document.getElementById('welcome-start-button');
        if (startButtonContainer) {
            startButtonContainer.remove();
        }

        // Clear the welcome message from UI
        messageRenderer.clearMessages();

        // Clear welcome pending state
        this._welcomePending = false;
        this._welcomeStartShown = false;

        // Process any queued widgets
        if (this._pendingWidgets.length > 0) {
            console.log('[ControlHandlers] Processing', this._pendingWidgets.length, 'queued widgets');
            for (const payload of this._pendingWidgets) {
                eventBus.emit(Events.WIDGET_RENDERED, payload);
            }
            this._pendingWidgets = [];
        }
    }

    /**
     * Cleanup and unsubscribe from events
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];

        // Reset state
        this.conversationConfig = null;
        this.enabledFeatures = null;
        this.deadline = null;
        this.currentItem = null;
        this._welcomeStartShown = false;
        this._welcomePending = false;
        this._pendingWidgets = [];

        this._initialized = false;
        console.log('[ControlHandlers] Destroyed');
    }

    /**
     * Check if handlers are initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const controlHandlers = new ControlHandlers();
export default controlHandlers;
