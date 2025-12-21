/**
 * Domain Module - Business Logic Layer
 *
 * Pure business logic with no DOM dependencies.
 * All UI updates happen via event bus emissions.
 *
 * Modules:
 * - config: Application configuration
 * - definition: Agent definitions
 * - conversation: Conversation management
 */

// Config domain
export {
    loadAppConfig,
    getAppConfig,
    getAppName,
    getWelcomeMessage,
    getToolsProviderUrl,
    isModelSelectionAllowed,
    getAvailableModels,
    getSelectedModelId,
    getSelectedModel,
    setSelectedModelId,
    handleModelChange,
} from './config.js';

// Definition domain
export {
    loadDefinitions,
    getDefinition,
    getDefinitions,
    getSelectedDefinition,
    getSelectedDefinitionId,
    selectDefinition,
    isProactiveDefinition,
    hasTemplate,
    shouldUseWebSocket,
    getDefinitionIcon,
    DEFAULT_ICONS,
} from './definition.js';

// Conversation domain
export {
    loadConversations,
    getConversations,
    loadConversation,
    createConversation,
    renameConversation,
    deleteConversation,
    deleteConversations,
    deleteAllUnpinned,
    getCurrentConversationId,
    setCurrentConversationId,
    togglePinned,
    isPinned,
    getPinnedConversations,
} from './conversation.js';
