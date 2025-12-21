/**
 * Control Plane Event Handlers
 *
 * Handles WebSocket protocol control-level messages:
 * - Conversation state (config, lifecycle, deadline)
 * - Item context and scoring
 * - Widget state and rendering
 * - Navigation requests
 * - Flow control (chat input, progress)
 *
 * These map to backend events from: application/protocol/control.py
 *
 * @module handlers/control-handlers
 */

import { Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { clearWidgets } from '../ui/renderers/widget-renderer.js';

// =============================================================================
// CONVERSATION HANDLERS
// =============================================================================

/**
 * Handler for control.conversation.config
 * Server sends conversation configuration/settings
 *
 * Payload:
 * - conversationId: string
 * - mode: string - "free_chat" | "template_guided" | "assessment"
 * - templateId: string (optional)
 * - settings: object - UI preferences, permissions
 * - features: object - Enabled features (canvas, widgets, etc.)
 */
function handleConversationConfig(context) {
    return payload => {
        console.log('[ControlHandler] Conversation config:', payload);

        // Store config for the conversation
        context.conversationConfig = payload;

        // Apply mode-specific UI adjustments
        if (payload.mode === 'assessment') {
            // Assessment mode: may hide progress, enable proctoring
            if (context.setAssessmentMode) {
                context.setAssessmentMode(true);
            }
        }

        // Enable/disable features based on server config
        if (payload.features) {
            context.enabledFeatures = payload.features;
        }
    };
}

/**
 * Handler for control.conversation.display
 * Server requests display state change
 *
 * Payload:
 * - state: string - "normal" | "minimized" | "fullscreen" | "hidden"
 * - reason: string - Why state changed
 * - metadata: object - Additional display instructions
 */
function handleConversationDisplay(context) {
    return payload => {
        console.log('[ControlHandler] Conversation display:', payload);

        // Update conversation display state
        if (context.setDisplayState) {
            context.setDisplayState(payload.state, payload.reason);
        }
    };
}

/**
 * Handler for control.conversation.deadline
 * Server updates conversation deadline (for timed assessments)
 *
 * Payload:
 * - conversationId: string
 * - deadline: string - ISO timestamp
 * - warningAt: string - When to show warning (optional)
 * - action: string - What happens at deadline ("pause" | "terminate")
 */
function handleConversationDeadline(context) {
    return payload => {
        console.log('[ControlHandler] Conversation deadline:', payload);

        // Store deadline
        context.deadline = new Date(payload.deadline);

        // Start countdown timer if UI component exists
        if (context.startDeadlineTimer) {
            context.startDeadlineTimer(payload.deadline, payload.warningAt);
        }
    };
}

/**
 * Handler for control.conversation.started
 * Conversation has transitioned to active state
 *
 * Payload:
 * - conversationId: string
 * - startedAt: string - ISO timestamp
 */
function handleConversationStarted(context) {
    return payload => {
        console.log('[ControlHandler] Conversation started:', payload);

        // Enable input controls
        if (context.enableChatInput) {
            context.enableChatInput(true);
        }

        // Emit local event for UI updates
        if (context.eventBus) {
            context.eventBus.emit(Events.CONVERSATION_UPDATED, {
                id: payload.conversationId,
                status: 'active',
            });
        }
    };
}

/**
 * Handler for control.conversation.paused
 * Conversation has been paused
 *
 * Payload:
 * - conversationId: string
 * - reason: string - Why paused
 * - pausedBy: string - "user" | "system" | "proctor"
 * - resumable: boolean
 */
function handleConversationPaused(context) {
    return payload => {
        console.log('[ControlHandler] Conversation paused:', payload);

        // Disable input
        if (context.enableChatInput) {
            context.enableChatInput(false);
        }

        // Show pause overlay
        if (context.showPauseOverlay) {
            context.showPauseOverlay(payload.reason, payload.resumable);
        }

        // Stop any deadline timers
        if (context.pauseDeadlineTimer) {
            context.pauseDeadlineTimer();
        }
    };
}

/**
 * Handler for control.conversation.resumed
 * Conversation has been resumed
 *
 * Payload:
 * - conversationId: string
 * - resumedAt: string - ISO timestamp
 * - remainingTime: number - Seconds remaining (if timed)
 */
function handleConversationResumed(context) {
    return payload => {
        console.log('[ControlHandler] Conversation resumed:', payload);

        // Re-enable input
        if (context.enableChatInput) {
            context.enableChatInput(true);
        }

        // Hide pause overlay
        if (context.hidePauseOverlay) {
            context.hidePauseOverlay();
        }

        // Resume deadline timer with remaining time
        if (payload.remainingTime && context.resumeDeadlineTimer) {
            context.resumeDeadlineTimer(payload.remainingTime);
        }
    };
}

/**
 * Handler for control.conversation.completed
 * Conversation has completed normally
 *
 * Payload:
 * - conversationId: string
 * - completedAt: string - ISO timestamp
 * - summary: object - Completion summary (optional)
 * - score: object - Final score (for assessments)
 */
function handleConversationCompleted(context) {
    return payload => {
        console.log('[ControlHandler] Conversation completed:', payload);

        // Disable further input
        if (context.enableChatInput) {
            context.enableChatInput(false);
        }

        // Show completion message/summary
        if (context.showCompletionSummary) {
            context.showCompletionSummary(payload.summary, payload.score);
        }

        // Emit local event
        if (context.eventBus) {
            context.eventBus.emit(Events.TEMPLATE_COMPLETE, payload);
        }
    };
}

/**
 * Handler for control.conversation.terminated
 * Conversation was terminated (abnormal end)
 *
 * Payload:
 * - conversationId: string
 * - reason: string - Why terminated
 * - terminatedBy: string - "user" | "system" | "timeout"
 */
function handleConversationTerminated(context) {
    return payload => {
        console.log('[ControlHandler] Conversation terminated:', payload);

        // Disable input
        if (context.enableChatInput) {
            context.enableChatInput(false);
        }

        // Show termination message
        if (context.showToast) {
            context.showToast('warning', `Conversation ended: ${payload.reason}`);
        }
    };
}

// =============================================================================
// ITEM HANDLERS
// =============================================================================

/**
 * Handler for control.item.context
 * Server sends context for a template item
 *
 * Payload:
 * - itemId: string
 * - templateId: string
 * - itemIndex: number - Position in template
 * - totalItems: number - Total items in template
 * - enableChatInput: boolean - Whether chat input is enabled for this item
 * - requireUserConfirmation: boolean - Whether to require confirmation before advancing
 * - confirmationButtonText: string - Text for confirmation button
 * - metadata: object - Item-specific metadata
 * - canNavigateBack: boolean
 * - canNavigateForward: boolean
 */
function handleItemContext(context) {
    return payload => {
        console.log('[ControlHandler] Item context received:', {
            itemId: payload.itemId,
            requireUserConfirmation: payload.requireUserConfirmation,
            confirmationButtonText: payload.confirmationButtonText,
            enableChatInput: payload.enableChatInput,
        });

        // Clear widgets from previous item
        clearWidgets();

        // Update progress indicator
        if (context.updateProgress) {
            context.updateProgress(payload.itemIndex, payload.totalItems);
        }

        // Update navigation buttons
        if (context.updateNavigationState) {
            context.updateNavigationState({
                canBack: payload.canNavigateBack,
                canForward: payload.canNavigateForward,
            });
        }

        // Apply chat input setting from item context
        if (context.enableChatInput && payload.enableChatInput !== undefined) {
            context.enableChatInput(payload.enableChatInput);
        }

        // Store current item context in global state (for widget renderer access)
        stateManager.set(StateKeys.CURRENT_ITEM_CONTEXT, payload);

        // Store current item context (includes requireUserConfirmation, confirmationButtonText)
        context.currentItem = payload;
    };
}

/**
 * Handler for control.item.score
 * Server sends score for a completed item
 *
 * Payload:
 * - itemId: string
 * - score: number - Score value
 * - maxScore: number - Maximum possible score
 * - feedback: string - Score explanation (optional)
 * - showToUser: boolean - Whether to display score
 */
function handleItemScore(context) {
    return payload => {
        console.log('[ControlHandler] Item score:', payload);

        // Only show if allowed
        if (payload.showToUser && context.showItemScore) {
            context.showItemScore(payload);
        }

        // Emit event for analytics/tracking
        if (context.eventBus) {
            context.eventBus.emit('item:scored', payload);
        }
    };
}

/**
 * Handler for control.item.timeout
 * Warning that item is about to expire
 *
 * Payload:
 * - itemId: string
 * - remainingSeconds: number
 * - action: string - What happens on timeout
 */
function handleItemTimeout(context) {
    return payload => {
        console.log('[ControlHandler] Item timeout warning:', payload);

        // Show warning if significant time remaining
        if (payload.remainingSeconds > 10 && context.showTimeWarning) {
            context.showTimeWarning(payload.remainingSeconds);
        }
    };
}

/**
 * Handler for control.item.expired
 * Item has timed out
 *
 * Payload:
 * - itemId: string
 * - action: string - What happened ("skipped" | "auto_submitted")
 */
function handleItemExpired(context) {
    return payload => {
        console.log('[ControlHandler] Item expired:', payload);

        if (context.showToast) {
            context.showToast('warning', 'Time expired for this item');
        }
    };
}

// =============================================================================
// WIDGET HANDLERS
// =============================================================================

/**
 * Handler for control.widget.state
 * Server updates widget state
 *
 * Payload:
 * - widgetId: string
 * - state: string - "pending" | "active" | "answered" | "expired"
 * - data: object - Widget-specific data
 */
function handleWidgetState(context) {
    return payload => {
        console.log('[ControlHandler] Widget state:', payload);

        if (context.updateWidgetState) {
            context.updateWidgetState(payload.widgetId, payload.state, payload.data);
        }
    };
}

/**
 * Handler for control.widget.render
 * Server requests widget rendering
 *
 * Payload:
 * - widgetId: string
 * - widgetType: string - Widget type identifier
 * - config: object - Widget configuration
 * - data: object - Widget data
 */
function handleWidgetRender(context) {
    return payload => {
        console.log('[ControlHandler] Widget render:', payload);

        if (context.renderWidget) {
            context.renderWidget(payload);
        }

        // Emit event for widget system
        if (context.eventBus) {
            context.eventBus.emit(Events.WIDGET_RENDERED, payload);
        }
    };
}

/**
 * Handler for control.widget.dismiss
 * Server requests widget dismissal
 *
 * Payload:
 * - widgetId: string
 * - reason: string - Why dismissed
 */
function handleWidgetDismiss(context) {
    return payload => {
        console.log('[ControlHandler] Widget dismiss:', payload);

        if (context.dismissWidget) {
            context.dismissWidget(payload.widgetId, payload.reason);
        }
    };
}

/**
 * Handler for control.widget.update
 * Server updates widget data/config
 *
 * Payload:
 * - widgetId: string
 * - updates: object - Partial updates to apply
 */
function handleWidgetUpdate(context) {
    return payload => {
        console.log('[ControlHandler] Widget update:', payload);

        if (context.updateWidget) {
            context.updateWidget(payload.widgetId, payload.updates);
        }
    };
}

// =============================================================================
// NAVIGATION HANDLERS
// =============================================================================

/**
 * Handler for control.navigation.request
 * Server requests navigation to specific item/section
 *
 * Payload:
 * - target: string - Navigation target ("next" | "prev" | "item:5")
 * - reason: string - Why navigating
 */
function handleNavigationRequest(context) {
    return payload => {
        console.log('[ControlHandler] Navigation request:', payload);

        if (context.navigateTo) {
            context.navigateTo(payload.target, payload.reason);
        }
    };
}

/**
 * Handler for control.navigation.ack
 * Server acknowledges navigation
 *
 * Payload:
 * - success: boolean
 * - currentPosition: number
 */
function handleNavigationAck(context) {
    return payload => {
        console.log('[ControlHandler] Navigation ack:', payload);
        // Usually no action needed, navigation was successful
    };
}

/**
 * Handler for control.navigation.denied
 * Server denies navigation request
 *
 * Payload:
 * - reason: string - Why denied
 * - requiredAction: string - What user must do first
 */
function handleNavigationDenied(context) {
    return payload => {
        console.log('[ControlHandler] Navigation denied:', payload);

        if (context.showToast) {
            context.showToast('warning', payload.reason);
        }
    };
}

// =============================================================================
// FLOW CONTROL HANDLERS
// =============================================================================

/**
 * Handler for control.flow.chatInput
 * Server controls chat input state
 *
 * Payload:
 * - enabled: boolean
 * - placeholder: string - Input placeholder text
 * - maxLength: number - Max input length
 * - submitLabel: string - Submit button label
 */
function handleFlowChatInput(context) {
    return payload => {
        console.log('[ControlHandler] Flow chat input:', payload);

        if (context.configureChatInput) {
            context.configureChatInput(payload);
        }

        if (context.enableChatInput) {
            context.enableChatInput(payload.enabled);
        }
    };
}

/**
 * Handler for control.flow.progress
 * Server sends progress update
 *
 * Payload:
 * - current: number
 * - total: number
 * - percentage: number
 * - label: string
 */
function handleFlowProgress(context) {
    return payload => {
        console.log('[ControlHandler] Flow progress:', payload);

        if (context.updateProgress) {
            context.updateProgress(payload.current, payload.total, payload.label);
        }

        // Emit for progress bar component
        if (context.eventBus) {
            context.eventBus.emit(Events.TEMPLATE_PROGRESS, payload);
        }
    };
}

// =============================================================================
// EXPORTS
// =============================================================================

/**
 * Control plane handlers registration
 *
 * @type {Array<{event: string, handler: Function, description: string}>}
 */
export const handlers = [
    // Conversation handlers
    {
        event: Events.CONTROL_CONVERSATION_CONFIG,
        handler: handleConversationConfig,
        description: 'Server sends conversation configuration',
    },
    {
        event: Events.CONTROL_CONVERSATION_DISPLAY,
        handler: handleConversationDisplay,
        description: 'Server requests display state change',
    },
    {
        event: Events.CONTROL_CONVERSATION_DEADLINE,
        handler: handleConversationDeadline,
        description: 'Server updates conversation deadline',
    },
    {
        event: Events.CONTROL_CONVERSATION_STARTED,
        handler: handleConversationStarted,
        description: 'Conversation transitioned to active state',
    },
    {
        event: Events.CONTROL_CONVERSATION_PAUSED,
        handler: handleConversationPaused,
        description: 'Conversation has been paused',
    },
    {
        event: Events.CONTROL_CONVERSATION_RESUMED,
        handler: handleConversationResumed,
        description: 'Conversation has been resumed',
    },
    {
        event: Events.CONTROL_CONVERSATION_COMPLETED,
        handler: handleConversationCompleted,
        description: 'Conversation completed normally',
    },
    {
        event: Events.CONTROL_CONVERSATION_TERMINATED,
        handler: handleConversationTerminated,
        description: 'Conversation was terminated abnormally',
    },

    // Item handlers
    {
        event: Events.CONTROL_ITEM_CONTEXT,
        handler: handleItemContext,
        description: 'Server sends template item context',
    },
    {
        event: Events.CONTROL_ITEM_SCORE,
        handler: handleItemScore,
        description: 'Server sends score for completed item',
    },
    {
        event: Events.CONTROL_ITEM_TIMEOUT,
        handler: handleItemTimeout,
        description: 'Warning that item is about to expire',
    },
    {
        event: Events.CONTROL_ITEM_EXPIRED,
        handler: handleItemExpired,
        description: 'Item has timed out',
    },

    // Widget handlers
    {
        event: Events.CONTROL_WIDGET_STATE,
        handler: handleWidgetState,
        description: 'Server updates widget state',
    },
    {
        event: Events.CONTROL_WIDGET_RENDER,
        handler: handleWidgetRender,
        description: 'Server requests widget rendering',
    },
    {
        event: Events.CONTROL_WIDGET_DISMISS,
        handler: handleWidgetDismiss,
        description: 'Server requests widget dismissal',
    },
    {
        event: Events.CONTROL_WIDGET_UPDATE,
        handler: handleWidgetUpdate,
        description: 'Server updates widget data/config',
    },

    // Navigation handlers
    {
        event: Events.CONTROL_NAVIGATION_REQUEST,
        handler: handleNavigationRequest,
        description: 'Server requests navigation',
    },
    {
        event: Events.CONTROL_NAVIGATION_ACK,
        handler: handleNavigationAck,
        description: 'Server acknowledges navigation',
    },
    {
        event: Events.CONTROL_NAVIGATION_DENIED,
        handler: handleNavigationDenied,
        description: 'Server denies navigation request',
    },

    // Flow control handlers
    {
        event: Events.CONTROL_FLOW_CHAT_INPUT,
        handler: handleFlowChatInput,
        description: 'Server controls chat input state',
    },
    {
        event: Events.CONTROL_FLOW_PROGRESS,
        handler: handleFlowProgress,
        description: 'Server sends progress update',
    },
];

export default handlers;
