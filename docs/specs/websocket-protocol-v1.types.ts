/**
 * Agent Host WebSocket Protocol v1.0.0 - TypeScript Interfaces
 *
 * Auto-generated from websocket-protocol-v1.md
 * Date: December 18, 2025
 *
 * This file provides type-safe interfaces for both frontend and backend
 * implementations of the Agent Host WebSocket protocol.
 */

// =============================================================================
// CORE TYPES
// =============================================================================

/** Message source identifier */
export type MessageSource = 'client' | 'server';

/** Protocol version */
export type ProtocolVersion = '1.0';

/** Message type planes */
export type MessagePlane = 'system' | 'control' | 'data';

// =============================================================================
// MESSAGE ENVELOPE
// =============================================================================

/**
 * Base message envelope - all messages wrap their payload in this structure
 * Inspired by CloudEvents specification
 */
export interface ProtocolMessage<T = unknown> {
    /** Unique message identifier (UUID or nanoid) */
    id: string;
    /** Hierarchical message type: plane.category.action */
    type: string;
    /** Protocol version (semver format) */
    version: ProtocolVersion;
    /** ISO 8601 timestamp with milliseconds */
    timestamp: string;
    /** Origin: client or server */
    source: MessageSource;
    /** Conversation context (null for connection-level messages) */
    conversationId: string | null;
    /** Message-specific data */
    payload: T;
}

// =============================================================================
// SYSTEM MESSAGES
// =============================================================================

export interface SystemConnectionEstablishedPayload {
    connectionId: string;
    conversationId: string;
    userId: string;
    definitionId?: string;
    resuming: boolean;
    serverTime: string;
}

export interface SystemConnectionResumePayload {
    conversationId: string;
    lastMessageId: string;
    lastItemIndex: number;
    clientState: {
        pendingWidgetIds: string[];
        inputContent?: string;
    };
}

export interface SystemConnectionResumedPayload {
    conversationId: string;
    resumedFromMessageId: string;
    currentItemIndex: number;
    missedMessages: number;
    stateValid: boolean;
}

export interface SystemConnectionClosePayload {
    reason: 'user_logout' | 'session_expired' | 'server_shutdown' | 'conversation_complete' | 'idle_timeout';
    code: number;
}

export interface SystemPingPongPayload {
    timestamp: string;
}

export interface SystemErrorPayload {
    category: 'transport' | 'authentication' | 'validation' | 'business' | 'server' | 'rate_limit';
    code: string;
    message: string;
    details?: Record<string, unknown>;
    isRetryable: boolean;
    retryAfterMs?: number;
}

// =============================================================================
// CONTROL PLANE - CONVERSATION LEVEL
// =============================================================================

export type DisplayMode = 'append' | 'replace';
export type ItemTimerMode = 'parallel' | 'focused' | 'aggregate';
export type WidgetCompletionBehavior = 'readonly' | 'text' | 'hidden';

export interface AuditConfig {
    enabled: boolean;
    captureKeystrokes: boolean;
    captureMouseClicks: boolean;
    captureMousePosition: boolean;
    captureFocusChanges: boolean;
    captureClipboard: boolean;
    batchIntervalMs: number;
    excludeWidgetTypes: string[];
}

export interface ConversationConfigPayload {
    templateId: string;
    templateName: string;
    totalItems: number;
    displayMode: DisplayMode;
    showConversationHistory: boolean;
    allowBackwardNavigation: boolean;
    allowConcurrentItemWidgets: boolean;
    allowSkip: boolean;
    enableChatInputInitially: boolean;
    displayProgressIndicator: boolean;
    displayFinalScoreReport: boolean;
    continueAfterCompletion: boolean;
    itemTimerMode?: ItemTimerMode;
    audit?: AuditConfig;
}

export interface FlowConfig {
    behavior: DisplayMode;
    maxVisibleMessages: number | null;
    autoScroll: boolean;
}

export interface CanvasConfig {
    width: number;
    height: number;
    background: string;
    gridEnabled: boolean;
    gridSize: number;
    snapToGrid: boolean;
    minZoom: number;
    maxZoom: number;
    initialZoom: number;
    initialViewport: { x: number; y: number };
}

export interface ConversationDisplayPayload {
    mode: 'flow' | 'canvas';
    flowConfig: FlowConfig | null;
    canvasConfig: CanvasConfig | null;
}

export interface ConversationDeadlinePayload {
    deadline: string;
    showWarning?: boolean;
    warningThresholdSeconds?: number;
}

export interface ConversationPausePayload {
    reason: string;
    pausedAt: string;
}

// =============================================================================
// CONTROL PLANE - ITEM LEVEL
// =============================================================================

export interface ItemContextPayload {
    itemId: string;
    itemIndex: number;
    totalItems: number;
    itemTitle?: string;
    enableChatInput: boolean;
    timeLimitSeconds: number | null;
    showRemainingTime: boolean;
    widgetCompletionBehavior: WidgetCompletionBehavior;
    conversationDeadline?: string;
}

export interface ItemScorePayload {
    itemId: string;
    score: number;
    maxScore: number;
    feedback?: string;
    correctAnswer?: string;
}

export interface ItemTimeoutPayload {
    itemId: string;
    action: 'auto_advance' | 'lock' | 'warn';
}

export interface ItemExpiredPayload {
    itemId: string;
    expiredAt: string;
}

// =============================================================================
// CONTROL PLANE - WIDGET LEVEL
// =============================================================================

export type WidgetState = 'active' | 'readonly' | 'disabled' | 'hidden';

export interface WidgetStatePayload {
    widgetId: string;
    state: WidgetState;
    clearValue?: boolean;
    reason?: string;
}

export interface WidgetFocusPayload {
    widgetId: string;
    highlight?: boolean;
    scrollIntoView?: boolean;
}

export interface WidgetValidationPayload {
    widgetId: string;
    valid: boolean;
    message?: string;
    details?: Record<string, unknown>;
}

export interface WidgetLayoutPayload {
    widgetId: string;
    layout: WidgetLayout;
    animate?: boolean;
    animationDuration?: number;
}

export interface WidgetMovedPayload {
    widgetId: string;
    position: Position;
}

export interface WidgetResizedPayload {
    widgetId: string;
    dimensions: Dimensions;
}

export interface WidgetDismissedPayload {
    widgetId: string;
    action: 'hide' | 'minimize' | 'collapse';
}

export type ConditionOperator = 'equals' | 'not_equals' | 'contains' | 'in' | 'greater_than' | 'less_than' | 'regex';
export type ConditionEffect = 'show' | 'hide' | 'enable' | 'disable' | 'focus';

export interface WidgetConditionPayload {
    widgetId: string;
    conditions: Array<{
        sourceWidget: string;
        operator: ConditionOperator;
        value: unknown;
        effect: ConditionEffect;
    }>;
    defaultState: WidgetState;
    evaluateOn: 'submit' | 'change';
}

// =============================================================================
// CONTROL PLANE - FLOW & NAVIGATION
// =============================================================================

export interface FlowStartPayload {
    // Empty or optional fields
}

export interface FlowPausePayload {
    reason: string;
}

export interface FlowCancelPayload {
    requestId?: string;
}

export interface NavigationPayload {
    currentItemId?: string;
    itemId?: string;
    reason?: string;
}

// =============================================================================
// CONTROL PLANE - AUDIT
// =============================================================================

export type AuditEventType = 'focus_change' | 'keystroke' | 'mouse_click' | 'mouse_move' | 'paste' | 'copy' | 'scroll' | 'visibility_change' | 'window_blur' | 'window_focus';

export type AuditElementType = 'widget' | 'chat' | 'canvas' | 'background' | 'toolbar' | 'navigation';

export interface AuditElementContext {
    type: AuditElementType;
    widgetId: string | null;
    widgetType?: string;
    itemId: string | null;
    region?: { x: number; y: number; width: number; height: number };
}

export interface AuditEvent {
    eventId: string;
    eventType: AuditEventType;
    timestamp: string;
    context: Record<string, unknown>;
}

export interface AuditFocusChangeContext {
    fromElement: AuditElementContext | null;
    toElement: AuditElementContext | null;
    focusDuration?: number;
}

export interface AuditKeystrokeContext {
    element: AuditElementContext;
    key: string;
    modifiers: Array<'shift' | 'ctrl' | 'alt' | 'meta'>;
    inputLength: number;
    cursorPosition?: number;
}

export interface AuditMouseClickContext {
    element: AuditElementContext;
    position: Position;
    button: 'left' | 'right' | 'middle';
    clickType: 'single' | 'double' | 'triple';
}

export interface AuditEventsPayload {
    userId: string;
    sessionId: string;
    batchId: string;
    events: AuditEvent[];
}

export interface AuditAckPayload {
    batchId: string;
    receivedCount: number;
    status: 'stored' | 'rejected';
}

export interface AuditFlushPayload {
    reason: string;
}

export interface AuditFlushedPayload {
    pendingBatches: number;
    totalEventsFlushed: number;
}

// =============================================================================
// DATA PLANE - CONTENT
// =============================================================================

export interface ContentChunkPayload {
    content: string;
    messageId: string;
    final: boolean;
}

export interface ContentCompletePayload {
    messageId: string;
    role: 'assistant' | 'user' | 'system';
    fullContent: string;
}

// =============================================================================
// DATA PLANE - TOOLS
// =============================================================================

export interface ToolCallPayload {
    callId: string;
    toolName: string;
    arguments: Record<string, unknown>;
}

export interface ToolResultPayload {
    callId: string;
    toolName: string;
    success: boolean;
    result: unknown;
    executionTimeMs?: number;
}

// =============================================================================
// DATA PLANE - USER MESSAGES & RESPONSES
// =============================================================================

export interface MessageSendPayload {
    content: string;
    attachments?: unknown[];
}

export interface ResponseSubmitPayload {
    itemId: string;
    widgetId: string;
    widgetType: string;
    value: unknown;
    metadata?: {
        selectionIndex?: number;
        timeSpentMs?: number;
        [key: string]: unknown;
    };
}

// =============================================================================
// WIDGET SYSTEM - CORE TYPES
// =============================================================================

export type WidgetType =
    | 'message'
    | 'multiple_choice'
    | 'free_text'
    | 'code_editor'
    | 'slider'
    | 'hotspot'
    | 'drag_drop'
    | 'dropdown'
    | 'iframe'
    | 'sticky_note'
    | 'image'
    | 'video'
    | 'graph_topology'
    | 'matrix_choice'
    | 'document_viewer'
    | 'file_upload'
    | 'rating'
    | 'date_picker'
    | 'drawing';

export type AnchorPosition = 'top-left' | 'top-center' | 'top-right' | 'center-left' | 'center' | 'center-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';

export type DismissAction = 'hide' | 'minimize' | 'collapse';

export interface Position {
    x: number;
    y: number;
}

export interface Dimensions {
    width?: number;
    height?: number;
    minWidth?: number;
    minHeight?: number;
    maxWidth?: number;
    maxHeight?: number;
}

export interface WidgetLayout {
    mode: 'flow' | 'canvas';
    position?: Position;
    dimensions?: Dimensions;
    anchor: AnchorPosition;
    zIndex?: number;
}

export interface WidgetConstraints {
    moveable: boolean;
    resizable: boolean;
    dismissable: boolean;
    dismissAction: DismissAction;
    selectable?: boolean;
    connectable?: boolean;
}

export interface WidgetRenderPayload<TConfig = unknown> {
    itemId: string;
    widgetId: string;
    widgetType: WidgetType;
    stem?: string;
    config: TConfig;
    required: boolean;
    skippable?: boolean;
    initialValue?: unknown;
    showUserResponse?: boolean;
    layout: WidgetLayout;
    constraints: WidgetConstraints;
}

// =============================================================================
// WIDGET CONFIGURATIONS
// =============================================================================

export interface MultipleChoiceConfig {
    options: string[];
    allowMultiple: boolean;
    shuffleOptions?: boolean;
    showLabels?: boolean;
    labelStyle?: 'letter' | 'number';
}

export interface FreeTextConfig {
    placeholder?: string;
    minLength?: number;
    maxLength?: number;
    multiline: boolean;
    rows?: number;
}

export interface CodeEditorConfig {
    language: string;
    initialCode?: string;
    minLines?: number;
    maxLines?: number;
    readOnly?: boolean;
    showLineNumbers?: boolean;
}

export interface SliderConfig {
    min: number;
    max: number;
    step: number;
    defaultValue?: number;
    showValue?: boolean;
    labels?: Record<string, string>;
}

export type DragDropVariant = 'category' | 'sequence' | 'graphical';

export interface DragDropItem {
    id: string;
    content: string;
    reusable?: boolean;
    icon?: string;
}

export interface DragDropZone {
    id: string;
    label: string;
    ordered?: boolean;
    slots?: number;
}

export interface DragDropPlaceholder {
    id: string;
    region: { x: number; y: number; width: number; height: number };
    accepts: string[] | null;
    hint?: string;
}

export interface DragDropConfig {
    variant: DragDropVariant;
    items: DragDropItem[];
    zones?: DragDropZone[];
    placeholders?: DragDropPlaceholder[];
    backgroundImage?: string;
    backgroundSize?: { width: number; height: number };
    allowMultiplePerZone?: boolean;
    requireAllPlaced?: boolean;
    shuffleItems?: boolean;
    showZoneCapacity?: boolean;
    showSlotNumbers?: boolean;
    showPlaceholderHints?: boolean;
    snapToPlaceholder?: boolean;
    allowFreePositioning?: boolean;
}

export interface GraphNodeType {
    typeId: string;
    label: string;
    icon?: string;
    color?: string;
    maxInstances?: number | null;
    properties?: Array<{
        name: string;
        type: 'text' | 'number' | 'select';
        required?: boolean;
        default?: unknown;
        options?: string[];
    }>;
}

export interface GraphEdgeType {
    typeId: string;
    label: string;
    style: 'arrow' | 'line' | 'dashed-arrow' | 'double-arrow';
    color?: string;
    bidirectional?: boolean;
}

export interface GraphRegion {
    regionId: string;
    label: string;
    color?: string;
    borderColor?: string;
}

export interface GraphTopologyConfig {
    mode: 'build' | 'view';
    nodeTypes: GraphNodeType[];
    edgeTypes: GraphEdgeType[];
    regions?: GraphRegion[];
    constraints?: {
        minNodes?: number;
        maxNodes?: number;
        minEdges?: number;
        maxEdges?: number;
        allowCycles?: boolean;
        allowSelfLoops?: boolean;
        requireConnected?: boolean;
    };
    initialGraph?: unknown;
    toolbar?: {
        showNodePalette?: boolean;
        showEdgeTools?: boolean;
        showRegionTools?: boolean;
        showLayoutTools?: boolean;
    };
    validation?: {
        rules: Array<{ rule: string; message: string }>;
    };
}

export interface MatrixChoiceRow {
    id: string;
    label: string;
}

export interface MatrixChoiceColumn {
    id: string;
    label: string;
    value?: number;
}

export interface MatrixChoiceConfig {
    layout: 'rows' | 'columns' | 'likert';
    rows: MatrixChoiceRow[];
    columns: MatrixChoiceColumn[];
    selectionMode: 'single' | 'multiple';
    requireAllRows?: boolean;
    shuffleRows?: boolean;
    shuffleColumns?: boolean;
    showRowNumbers?: boolean;
    stickyHeader?: boolean;
}

export interface DocumentSection {
    sectionId: string;
    heading: string;
    anchorId: string;
    requiredReadTime?: number;
    checkpoint?: boolean;
}

export interface EmbeddedWidget {
    anchorId: string;
    widgetId: string;
    widgetType: WidgetType;
    config: unknown;
}

export interface DocumentViewerConfig {
    content?: string;
    contentUrl?: string;
    contentType: 'markdown' | 'html' | 'text';
    tableOfContents?: {
        enabled: boolean;
        position: 'left' | 'right';
        collapsible?: boolean;
        defaultExpanded?: boolean;
        maxDepth?: number;
    };
    navigation?: {
        showProgress?: boolean;
        showPageNumbers?: boolean;
        enableSearch?: boolean;
        enableHighlight?: boolean;
    };
    sections?: DocumentSection[];
    embeddedWidgets?: EmbeddedWidget[];
    readingMode?: {
        fontSize?: 'small' | 'medium' | 'large';
        lineHeight?: number;
        theme?: 'light' | 'dark' | 'auto';
    };
}

export interface HotspotRegion {
    id: string;
    shape: 'circle' | 'rect' | 'polygon';
    coords: Record<string, unknown>;
    label?: string;
    correct?: boolean;
}

export interface HotspotConfig {
    image: string;
    imageSize: { width: number; height: number };
    regions: HotspotRegion[];
    selectionMode: 'single' | 'multiple';
    showLabels?: boolean;
    highlightOnHover?: boolean;
    showFeedbackImmediately?: boolean;
}

export interface DrawingToolConfig {
    enabled: boolean;
    colors?: string[];
    sizes?: number[];
    opacity?: number;
    types?: string[];
    fonts?: string[];
}

export interface DrawingConfig {
    canvasSize: { width: number; height: number };
    backgroundImage?: string | null;
    backgroundColor?: string;
    tools: {
        pen?: DrawingToolConfig;
        highlighter?: DrawingToolConfig;
        eraser?: DrawingToolConfig;
        shapes?: DrawingToolConfig;
        text?: DrawingToolConfig;
    };
    initialDrawing?: unknown;
    allowUndo?: boolean;
    maxUndoSteps?: number;
}

export interface FileUploadConfig {
    accept: string[];
    maxFileSize: number;
    maxFiles: number;
    minFiles?: number;
    allowDragDrop?: boolean;
    showPreview?: boolean;
    previewMaxHeight?: number;
    uploadEndpoint: string;
    uploadMethod?: 'POST' | 'PUT';
    uploadHeaders?: Record<string, string>;
    autoUpload?: boolean;
    showProgress?: boolean;
    allowRemove?: boolean;
    placeholder?: string;
    helperText?: string;
}

export interface RatingConfig {
    style: 'stars' | 'numeric' | 'emoji' | 'thumbs';
    maxRating: number;
    allowHalf?: boolean;
    defaultValue?: number | null;
    showValue?: boolean;
    showLabels?: boolean;
    labels?: Record<string, string>;
    size?: 'small' | 'medium' | 'large';
    color?: string;
    emptyColor?: string;
    icon?: string;
    required?: boolean;
}

export interface DatePickerConfig {
    mode: 'date' | 'time' | 'datetime' | 'daterange';
    format: string;
    displayFormat?: string;
    placeholder?: string;
    minDate?: string;
    maxDate?: string;
    disabledDates?: string[];
    disabledDaysOfWeek?: number[];
    defaultValue?: string | null;
    showTodayButton?: boolean;
    showClearButton?: boolean;
    weekStartsOn?: number;
    locale?: string;
    timezone?: string;
    required?: boolean;
}

export interface DropdownOption {
    value: string;
    label: string;
    icon?: string;
    disabled?: boolean;
    group?: string;
}

export interface DropdownGroup {
    id: string;
    label: string;
}

export interface DropdownConfig {
    options: DropdownOption[];
    groups?: DropdownGroup[];
    multiple: boolean;
    searchable?: boolean;
    clearable?: boolean;
    placeholder?: string;
    noOptionsMessage?: string;
    maxSelections?: number | null;
    minSelections?: number;
    creatable?: boolean;
    defaultValue?: string | string[] | null;
    disabled?: boolean;
    loading?: boolean;
    virtualized?: boolean;
    maxDropdownHeight?: number;
}

export interface ImageConfig {
    src: string;
    alt: string;
    caption?: string;
    width?: number;
    height?: number;
    objectFit?: 'contain' | 'cover' | 'fill' | 'none';
    zoomable?: boolean;
    maxZoom?: number;
    pannable?: boolean;
    showControls?: boolean;
    downloadable?: boolean;
    fallbackSrc?: string;
    lazyLoad?: boolean;
    borderRadius?: number;
    shadow?: boolean;
}

export interface VideoCaption {
    language: string;
    label: string;
    src: string;
}

export interface VideoQuality {
    label: string;
    src: string;
}

export interface VideoChapter {
    title: string;
    startTime: number;
}

export interface VideoCheckpoint {
    checkpointId: string;
    timestamp: number;
    pauseOnReach?: boolean;
    required?: boolean;
    widget?: {
        widgetId: string;
        widgetType: WidgetType;
        config: unknown;
    };
    action?: string;
    note?: string;
}

export interface VideoConfig {
    src: string;
    poster?: string;
    title?: string;
    duration?: number;
    autoplay?: boolean;
    muted?: boolean;
    loop?: boolean;
    controls?: {
        play?: boolean;
        pause?: boolean;
        seek?: boolean;
        volume?: boolean;
        fullscreen?: boolean;
        playbackSpeed?: boolean;
        captions?: boolean;
        quality?: boolean;
    };
    playbackSpeeds?: number[];
    captions?: VideoCaption[];
    qualities?: VideoQuality[];
    checkpoints?: VideoCheckpoint[];
    chapters?: VideoChapter[];
    requiredWatchPercentage?: number;
    preventSkipAhead?: boolean;
    trackProgress?: boolean;
}

export interface StickyNoteStyle {
    backgroundColor?: string;
    textColor?: string;
    fontSize?: number;
    fontFamily?: string;
    shadow?: boolean;
    rotation?: number;
}

export interface StickyNoteConfig {
    content: string;
    editable?: boolean;
    maxLength?: number;
    placeholder?: string;
    style?: StickyNoteStyle;
    showTimestamp?: boolean;
    showAuthor?: boolean;
    author?: string;
    createdAt?: string;
    pinned?: boolean;
    minimizable?: boolean;
    minimized?: boolean;
}

// =============================================================================
// WIDGET RESPONSE VALUES
// =============================================================================

export type MultipleChoiceValue = string | string[];
export type FreeTextValue = string;
export type CodeEditorValue = string;
export type SliderValue = number;

export interface DragDropCategoryValue {
    [zoneId: string]: string[];
}

export interface DragDropGraphicalValue {
    placements: Array<{ placeholderId: string; itemId: string }>;
    freePositions?: Array<{ itemId: string; position: Position }>;
}

export interface GraphTopologyValue {
    nodes: Array<{
        nodeId: string;
        typeId: string;
        position: Position;
        properties: Record<string, unknown>;
    }>;
    edges: Array<{
        edgeId: string;
        typeId: string;
        sourceNodeId: string;
        targetNodeId: string;
    }>;
    regions?: Array<{
        regionId: string;
        typeId: string;
        bounds: { x: number; y: number; width: number; height: number };
        containedNodes: string[];
    }>;
}

export interface MatrixChoiceValue {
    selections: Record<string, string[]>;
}

export interface DocumentViewerValue {
    readSections: string[];
    timeSpent: number;
    highlights?: Array<{
        sectionId: string;
        text: string;
        color: string;
    }>;
    embeddedResponses?: Record<string, { value: unknown }>;
}

export interface HotspotValue {
    selectedRegions: string[];
}

export interface DrawingValue {
    format: 'svg' | 'png';
    data: string;
    png_base64?: string;
}

export interface FileUploadFile {
    fileId: string;
    filename: string;
    mimeType: string;
    size: number;
    uploadedAt: string;
    url: string;
}

export interface FileUploadValue {
    files: FileUploadFile[];
}

export type RatingValue = number;

export type DatePickerValue = string | { start: string; end: string };

export type DropdownValue = string | string[];

export interface ImageValue {
    viewed: boolean;
    zoomLevel?: number;
    viewDuration?: number;
}

export interface VideoValue {
    watchedPercentage: number;
    totalWatchTime: number;
    completedCheckpoints: string[];
    checkpointResponses?: Record<string, { value: unknown }>;
    lastPosition: number;
    playbackEvents?: Array<{
        event: string;
        timestamp?: number;
        from?: number;
        to?: number;
        time: string;
    }>;
}

export interface StickyNoteValue {
    content: string;
    editedAt?: string;
}

// =============================================================================
// CANVAS SYSTEM
// =============================================================================

export type CanvasMode = 'select' | 'pan' | 'connect' | 'annotate' | 'draw' | 'presentation';
export type ConnectionType = 'arrow' | 'line' | 'curve' | 'elbow' | 'double-arrow';
export type ConnectionAnchor = 'auto' | 'top' | 'right' | 'bottom' | 'left' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
export type BackgroundPattern = 'none' | 'dots' | 'lines' | 'crosshatch' | 'custom';
export type AlignmentOption = 'left' | 'center-horizontal' | 'right' | 'top' | 'center-vertical' | 'bottom';
export type SelectionMethod = 'click' | 'ctrl_click' | 'shift_click' | 'lasso' | 'marquee';
export type AnnotationType = 'sticky_note' | 'callout' | 'highlight' | 'drawing' | 'shape' | 'text';

export interface CanvasFullConfig {
    canvas: {
        width: number;
        height: number;
        backgroundColor?: string;
        backgroundImage?: string | null;
        backgroundPattern?: BackgroundPattern;
    };
    grid: {
        enabled: boolean;
        size: number;
        snapToGrid: boolean;
        visible: boolean;
        color?: string;
    };
    zoom: {
        initial: number;
        min: number;
        max: number;
        step: number;
    };
    viewport: {
        initialX: number;
        initialY: number;
        panEnabled: boolean;
        panButton: 'left' | 'middle' | 'right';
    };
    minimap?: {
        enabled: boolean;
        position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
        size: { width: number; height: number };
    };
    features: {
        connections: boolean;
        groups: boolean;
        layers: boolean;
        annotations: boolean;
        multiSelect: boolean;
        collaboration: boolean;
    };
}

export interface ConnectionStyle {
    type: ConnectionType;
    color: string;
    width?: number;
    dash?: string | null;
    animate?: boolean;
}

export interface ConnectionLabel {
    text: string;
    position: 'start' | 'middle' | 'end';
}

export interface ConnectionEndpoint {
    widgetId: string;
    anchor: ConnectionAnchor;
}

export interface ConnectionCondition {
    sourceWidget: string;
    operator: ConditionOperator;
    value: unknown;
}

export interface ConnectionCreatePayload {
    connectionId: string;
    source: ConnectionEndpoint;
    target: ConnectionEndpoint;
    style: ConnectionStyle;
    label?: ConnectionLabel;
    interactive?: boolean;
    condition?: ConnectionCondition | null;
}

export interface GroupStyle {
    backgroundColor?: string;
    borderColor?: string;
    borderRadius?: number;
}

export interface GroupCreatePayload {
    groupId: string;
    title: string;
    widgetIds: string[];
    style?: GroupStyle;
    collapsible?: boolean;
    collapsed?: boolean;
    draggable?: boolean;
    layout?: {
        position: Position;
        padding?: number;
    };
}

export interface LayerCreatePayload {
    layerId: string;
    name: string;
    visible: boolean;
    locked: boolean;
    opacity: number;
    zIndex: number;
}

export interface SelectionPayload {
    widgetIds: string[];
    groupIds: string[];
    connectionIds: string[];
    selectionMethod?: SelectionMethod;
}

export interface ViewportFocusTarget {
    type: 'widget' | 'group' | 'widgets' | 'point' | 'region';
    widgetId?: string;
    widgetIds?: string[];
    groupId?: string;
    x?: number;
    y?: number;
    width?: number;
    height?: number;
}

export interface ViewportPayload {
    action: 'focus' | 'pan' | 'panBy' | 'zoom' | 'zoomToFit' | 'zoomToSelection' | 'reset';
    target?: ViewportFocusTarget;
    position?: Position;
    offset?: Position;
    zoom?: number;
    padding?: number;
    animate?: boolean;
    animationDuration?: number;
    animationEasing?: string;
}

export interface PresentationStep {
    stepId: string;
    target: ViewportFocusTarget;
    zoom?: number;
    narration?: string;
    duration?: number | null;
    action: 'auto_advance' | 'await_click' | 'await_interaction' | 'await_complete' | 'await_all_complete' | 'manual';
}

export interface PresentationStartPayload {
    presentationId: string;
    title: string;
    steps: PresentationStep[];
    controls: {
        showProgress?: boolean;
        allowSkip?: boolean;
        allowBack?: boolean;
    };
}

export interface BookmarkCreatePayload {
    bookmarkId: string;
    name: string;
    description?: string;
    target: ViewportFocusTarget;
    zoom?: number;
    icon?: string;
    color?: string;
    showInNavigation?: boolean;
    sortOrder?: number;
}

export interface CommentCreatePayload {
    commentId: string;
    threadId: string;
    attachedTo: {
        type: 'widget' | 'canvas' | 'connection';
        widgetId?: string;
        connectionId?: string;
    };
    position: Position;
    author: {
        userId: string;
        name: string;
        avatar?: string;
    };
    content: string;
    timestamp: string;
    resolved: boolean;
}

export interface HistoryEntry {
    entryId: string;
    timestamp: string;
    action: string;
    description: string;
    widgetId?: string;
    canRevert: boolean;
}

export interface WidgetTemplate {
    templateId: string;
    name: string;
    category: string;
    preview?: string;
    widgetType: WidgetType;
    config: unknown;
}

// =============================================================================
// IFRAME WIDGET
// =============================================================================

export type IframeCommunicationMode = 'relay' | 'independent';

export interface IframeConfig {
    src: string;
    communicationMode: IframeCommunicationMode;
    sandbox: string[];
    allow: string[];
    loading: 'eager' | 'lazy';
    dimensions: {
        width: number;
        height: number;
        aspectRatio?: string;
    };
    initParams?: Record<string, unknown>;
    messageOrigin: string;
    timeout?: number;
    fallbackContent?: string;
}

export interface IframeEventPayload {
    widgetId: string;
    eventType: string;
    data: Record<string, unknown>;
    timestamp: string;
}

export interface IframeCommandPayload {
    widgetId: string;
    command: string;
    params?: Record<string, unknown>;
}

export interface IframeStatePayload {
    widgetId: string;
    state: Record<string, unknown>;
    stateVersion: number;
}

export interface IframeErrorPayload {
    widgetId: string;
    errorType: 'load_failed' | 'timeout' | 'sandbox_blocked' | 'origin_mismatch' | 'communication_error' | 'content_error';
    message: string;
    details?: Record<string, unknown>;
}

// =============================================================================
// WEBSOCKET CLOSE CODES
// =============================================================================

export enum StandardCloseCode {
    NormalClosure = 1000,
    GoingAway = 1001,
    ProtocolError = 1002,
    UnsupportedData = 1003,
    NoStatusReceived = 1005,
    AbnormalClosure = 1006,
    InvalidPayloadData = 1007,
    PolicyViolation = 1008,
    MessageTooBig = 1009,
    MandatoryExtension = 1010,
    InternalError = 1011,
    ServiceRestart = 1012,
    TryAgainLater = 1013,
    BadGateway = 1014,
    TLSHandshake = 1015,
}

export enum AppCloseCode {
    AuthenticationRequired = 4000,
    AuthenticationExpired = 4001,
    AuthenticationInvalid = 4002,
    ConversationNotFound = 4003,
    ConversationEnded = 4004,
    DefinitionNotFound = 4005,
    RateLimited = 4006,
    DuplicateConnection = 4007,
    IdleTimeout = 4008,
    MaintenanceMode = 4009,
    VersionMismatch = 4010,
    PayloadTooLarge = 4011,
    InvalidMessage = 4012,
    ResourceExhausted = 4013,
    UpstreamError = 4014,
    ConversationPaused = 4015,
}

// =============================================================================
// MESSAGE TYPE CONSTANTS
// =============================================================================

export const MessageTypes = {
    // System
    SYSTEM_CONNECTION_ESTABLISHED: 'system.connection.established',
    SYSTEM_CONNECTION_RESUME: 'system.connection.resume',
    SYSTEM_CONNECTION_RESUMED: 'system.connection.resumed',
    SYSTEM_CONNECTION_CLOSE: 'system.connection.close',
    SYSTEM_PING: 'system.ping',
    SYSTEM_PONG: 'system.pong',
    SYSTEM_ERROR: 'system.error',

    // Control - Conversation
    CONTROL_CONVERSATION_CONFIG: 'control.conversation.config',
    CONTROL_CONVERSATION_DISPLAY: 'control.conversation.display',
    CONTROL_CONVERSATION_DEADLINE: 'control.conversation.deadline',
    CONTROL_CONVERSATION_PAUSE: 'control.conversation.pause',
    CONTROL_CONVERSATION_RESUME: 'control.conversation.resume',
    CONTROL_CONVERSATION_COMPLETE: 'control.conversation.complete',

    // Control - Item
    CONTROL_ITEM_CONTEXT: 'control.item.context',
    CONTROL_ITEM_SCORE: 'control.item.score',
    CONTROL_ITEM_TIMEOUT: 'control.item.timeout',
    CONTROL_ITEM_EXPIRED: 'control.item.expired',

    // Control - Widget
    CONTROL_WIDGET_STATE: 'control.widget.state',
    CONTROL_WIDGET_FOCUS: 'control.widget.focus',
    CONTROL_WIDGET_VALIDATION: 'control.widget.validation',
    CONTROL_WIDGET_LAYOUT: 'control.widget.layout',
    CONTROL_WIDGET_MOVED: 'control.widget.moved',
    CONTROL_WIDGET_RESIZED: 'control.widget.resized',
    CONTROL_WIDGET_DISMISSED: 'control.widget.dismissed',
    CONTROL_WIDGET_CONDITION: 'control.widget.condition',

    // Control - Flow
    CONTROL_FLOW_START: 'control.flow.start',
    CONTROL_FLOW_PAUSE: 'control.flow.pause',
    CONTROL_FLOW_RESUME: 'control.flow.resume',
    CONTROL_FLOW_CANCEL: 'control.flow.cancel',

    // Control - Navigation
    CONTROL_NAVIGATION_NEXT: 'control.navigation.next',
    CONTROL_NAVIGATION_PREVIOUS: 'control.navigation.previous',
    CONTROL_NAVIGATION_SKIP: 'control.navigation.skip',

    // Control - Audit
    CONTROL_AUDIT_CONFIG: 'control.audit.config',
    CONTROL_AUDIT_FLUSH: 'control.audit.flush',

    // Control - Canvas
    CONTROL_CANVAS_CONFIG: 'control.canvas.config',
    CONTROL_CANVAS_VIEWPORT: 'control.canvas.viewport',
    CONTROL_CANVAS_ZOOM: 'control.canvas.zoom',
    CONTROL_CANVAS_MODE: 'control.canvas.mode',
    CONTROL_CANVAS_CONNECTION_CREATE: 'control.canvas.connection.create',
    CONTROL_CANVAS_CONNECTION_UPDATE: 'control.canvas.connection.update',
    CONTROL_CANVAS_CONNECTION_DELETE: 'control.canvas.connection.delete',
    CONTROL_CANVAS_CONNECTION_CREATED: 'control.canvas.connection.created',
    CONTROL_CANVAS_GROUP_CREATE: 'control.canvas.group.create',
    CONTROL_CANVAS_GROUP_UPDATE: 'control.canvas.group.update',
    CONTROL_CANVAS_GROUP_ADD: 'control.canvas.group.add',
    CONTROL_CANVAS_GROUP_REMOVE: 'control.canvas.group.remove',
    CONTROL_CANVAS_GROUP_DELETE: 'control.canvas.group.delete',
    CONTROL_CANVAS_GROUP_TOGGLED: 'control.canvas.group.toggled',
    CONTROL_CANVAS_LAYER_CREATE: 'control.canvas.layer.create',
    CONTROL_CANVAS_LAYER_UPDATE: 'control.canvas.layer.update',
    CONTROL_CANVAS_LAYER_ASSIGN: 'control.canvas.layer.assign',
    CONTROL_CANVAS_LAYER_TOGGLED: 'control.canvas.layer.toggled',
    CONTROL_CANVAS_SELECTION_SET: 'control.canvas.selection.set',
    CONTROL_CANVAS_SELECTION_CHANGED: 'control.canvas.selection.changed',
    CONTROL_CANVAS_PRESENTATION_START: 'control.canvas.presentation.start',
    CONTROL_CANVAS_PRESENTATION_STEP: 'control.canvas.presentation.step',
    CONTROL_CANVAS_PRESENTATION_END: 'control.canvas.presentation.end',
    CONTROL_CANVAS_PRESENTATION_NAVIGATED: 'control.canvas.presentation.navigated',
    CONTROL_CANVAS_BOOKMARK_CREATE: 'control.canvas.bookmark.create',
    CONTROL_CANVAS_BOOKMARK_UPDATE: 'control.canvas.bookmark.update',
    CONTROL_CANVAS_BOOKMARK_DELETE: 'control.canvas.bookmark.delete',
    CONTROL_CANVAS_BOOKMARK_NAVIGATE: 'control.canvas.bookmark.navigate',
    CONTROL_CANVAS_BOOKMARK_CREATED: 'control.canvas.bookmark.created',

    // Control - IFRAME
    CONTROL_IFRAME_RESIZE: 'control.iframe.resize',
    CONTROL_IFRAME_NAVIGATE: 'control.iframe.navigate',

    // Data - Content
    DATA_CONTENT_CHUNK: 'data.content.chunk',
    DATA_CONTENT_COMPLETE: 'data.content.complete',

    // Data - Tools
    DATA_TOOL_CALL: 'data.tool.call',
    DATA_TOOL_RESULT: 'data.tool.result',

    // Data - Messages
    DATA_MESSAGE_SEND: 'data.message.send',
    DATA_MESSAGE_ACK: 'data.message.ack',

    // Data - Responses
    DATA_RESPONSE_SUBMIT: 'data.response.submit',

    // Data - Annotations
    DATA_ANNOTATION_CREATE: 'data.annotation.create',
    DATA_ANNOTATION_CREATED: 'data.annotation.created',

    // Data - Audit
    DATA_AUDIT_EVENTS: 'data.audit.events',
    DATA_AUDIT_ACK: 'data.audit.ack',
    DATA_AUDIT_FLUSHED: 'data.audit.flushed',

    // Data - IFRAME
    DATA_IFRAME_EVENT: 'data.iframe.event',
    DATA_IFRAME_COMMAND: 'data.iframe.command',
    DATA_IFRAME_STATE: 'data.iframe.state',
    DATA_IFRAME_ERROR: 'data.iframe.error',
} as const;

export type MessageType = (typeof MessageTypes)[keyof typeof MessageTypes];

// =============================================================================
// TYPED MESSAGE HELPERS
// =============================================================================

/** Helper type to create typed protocol messages */
export type TypedMessage<T extends string, P> = ProtocolMessage<P> & { type: T };

/** System messages */
export type SystemConnectionEstablishedMessage = TypedMessage<'system.connection.established', SystemConnectionEstablishedPayload>;
export type SystemConnectionResumeMessage = TypedMessage<'system.connection.resume', SystemConnectionResumePayload>;
export type SystemConnectionResumedMessage = TypedMessage<'system.connection.resumed', SystemConnectionResumedPayload>;
export type SystemConnectionCloseMessage = TypedMessage<'system.connection.close', SystemConnectionClosePayload>;
export type SystemPingMessage = TypedMessage<'system.ping', SystemPingPongPayload>;
export type SystemPongMessage = TypedMessage<'system.pong', SystemPingPongPayload>;
export type SystemErrorMessage = TypedMessage<'system.error', SystemErrorPayload>;

/** Control messages */
export type ConversationConfigMessage = TypedMessage<'control.conversation.config', ConversationConfigPayload>;
export type ConversationDisplayMessage = TypedMessage<'control.conversation.display', ConversationDisplayPayload>;
export type ItemContextMessage = TypedMessage<'control.item.context', ItemContextPayload>;
export type WidgetStateMessage = TypedMessage<'control.widget.state', WidgetStatePayload>;
export type WidgetRenderMessage = TypedMessage<'data.widget.render', WidgetRenderPayload>;

/** Data messages */
export type ContentChunkMessage = TypedMessage<'data.content.chunk', ContentChunkPayload>;
export type ContentCompleteMessage = TypedMessage<'data.content.complete', ContentCompletePayload>;
export type ResponseSubmitMessage = TypedMessage<'data.response.submit', ResponseSubmitPayload>;
export type AuditEventsMessage = TypedMessage<'data.audit.events', AuditEventsPayload>;

/** Union of all server-to-client messages */
export type ServerMessage =
    | SystemConnectionEstablishedMessage
    | SystemConnectionResumedMessage
    | SystemConnectionCloseMessage
    | SystemPongMessage
    | SystemErrorMessage
    | ConversationConfigMessage
    | ConversationDisplayMessage
    | ItemContextMessage
    | WidgetStateMessage
    | WidgetRenderMessage
    | ContentChunkMessage
    | ContentCompleteMessage;

/** Union of all client-to-server messages */
export type ClientMessage =
    | SystemConnectionResumeMessage
    | SystemPingMessage
    | TypedMessage<'control.flow.start', FlowStartPayload>
    | TypedMessage<'control.flow.pause', FlowPausePayload>
    | TypedMessage<'control.navigation.next', NavigationPayload>
    | TypedMessage<'control.navigation.previous', NavigationPayload>
    | TypedMessage<'data.message.send', MessageSendPayload>
    | ResponseSubmitMessage
    | AuditEventsMessage;

// =============================================================================
// FACTORY FUNCTIONS
// =============================================================================

/**
 * Create a protocol message with proper envelope structure
 */
export function createMessage<T>(
    type: string,
    payload: T,
    options: {
        conversationId?: string | null;
        source?: MessageSource;
    } = {}
): ProtocolMessage<T> {
    return {
        id: crypto.randomUUID(),
        type,
        version: '1.0',
        timestamp: new Date().toISOString(),
        source: options.source ?? 'client',
        conversationId: options.conversationId ?? null,
        payload,
    };
}

/**
 * Type guard to check if a message is of a specific type
 */
export function isMessageType<T extends string, P>(message: ProtocolMessage<unknown>, type: T): message is TypedMessage<T, P> {
    return message.type === type;
}

/**
 * Calculate exponential backoff delay for reconnection
 */
export function calculateReconnectBackoff(attempt: number): number {
    const baseDelay = 1000;
    const maxDelay = 30000;
    const jitter = Math.random() * 1000;
    return Math.min(baseDelay * Math.pow(2, attempt) + jitter, maxDelay);
}
