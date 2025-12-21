/**
 * Canvas Element Web Component
 * A draggable, resizable container for canvas items.
 *
 * Attributes:
 * - element-id: Unique identifier
 * - x, y: Position in world coordinates
 * - width, height: Dimensions
 * - locked: Prevent interaction
 * - selected: Selection state
 * - resizable: Allow resizing
 * - draggable: Allow dragging (default: true)
 *
 * Events:
 * - ax-element-move: Position changed
 * - ax-element-resize: Size changed
 * - ax-element-select: Selected/deselected
 */

class AxCanvasElement extends HTMLElement {
    static get observedAttributes() {
        return ['element-id', 'x', 'y', 'width', 'height', 'locked', 'selected', 'resizable', 'draggable'];
    }

    constructor() {
        super();
        this.attachShadow({ mode: 'open' });

        this._isDragging = false;
        this._isResizing = false;
        this._resizeHandle = null;
        this._startPos = null;
        this._startSize = null;
    }

    // Attribute getters
    get elementId() {
        return this.getAttribute('element-id') || '';
    }

    get x() {
        return parseFloat(this.getAttribute('x')) || 0;
    }
    set x(val) {
        this.setAttribute('x', val);
    }

    get y() {
        return parseFloat(this.getAttribute('y')) || 0;
    }
    set y(val) {
        this.setAttribute('y', val);
    }

    get width() {
        return parseFloat(this.getAttribute('width')) || 200;
    }
    set width(val) {
        this.setAttribute('width', val);
    }

    get height() {
        return parseFloat(this.getAttribute('height')) || 150;
    }
    set height(val) {
        this.setAttribute('height', val);
    }

    get locked() {
        return this.hasAttribute('locked');
    }

    get selected() {
        return this.hasAttribute('selected');
    }
    set selected(val) {
        if (val) this.setAttribute('selected', '');
        else this.removeAttribute('selected');
    }

    get resizable() {
        return this.hasAttribute('resizable');
    }

    get isDraggable() {
        return !this.hasAttribute('draggable') || this.getAttribute('draggable') !== 'false';
    }

    connectedCallback() {
        this.render();
        this._updatePosition();
        this._bindEvents();
    }

    disconnectedCallback() {
        this._unbindEvents();
    }

    attributeChangedCallback(name, oldVal, newVal) {
        if (oldVal === newVal) return;
        if (name === 'x' || name === 'y') {
            this._updatePosition();
        } else if (name === 'width' || name === 'height') {
            this._updateSize();
        } else if (name === 'selected') {
            this._updateSelection();
        }
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    position: absolute;
                    display: block;
                    box-sizing: border-box;
                }

                .element-container {
                    width: 100%;
                    height: 100%;
                    background: var(--element-bg, #fff);
                    border: 2px solid var(--element-border, #dee2e6);
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                    transition: border-color 0.15s ease, box-shadow 0.15s ease;
                }

                :host([selected]) .element-container {
                    border-color: var(--primary-color, #0d6efd);
                    box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.2);
                }

                :host([locked]) .element-container {
                    opacity: 0.7;
                }

                .content {
                    width: 100%;
                    height: 100%;
                    padding: 8px;
                    overflow: auto;
                }

                .resize-handles {
                    display: none;
                }

                :host([selected][resizable]:not([locked])) .resize-handles {
                    display: block;
                }

                .resize-handle {
                    position: absolute;
                    width: 10px;
                    height: 10px;
                    background: var(--primary-color, #0d6efd);
                    border: 2px solid #fff;
                    border-radius: 2px;
                    z-index: 10;
                }

                .resize-handle.nw { top: -5px; left: -5px; cursor: nwse-resize; }
                .resize-handle.n { top: -5px; left: 50%; transform: translateX(-50%); cursor: ns-resize; }
                .resize-handle.ne { top: -5px; right: -5px; cursor: nesw-resize; }
                .resize-handle.e { top: 50%; right: -5px; transform: translateY(-50%); cursor: ew-resize; }
                .resize-handle.se { bottom: -5px; right: -5px; cursor: nwse-resize; }
                .resize-handle.s { bottom: -5px; left: 50%; transform: translateX(-50%); cursor: ns-resize; }
                .resize-handle.sw { bottom: -5px; left: -5px; cursor: nesw-resize; }
                .resize-handle.w { top: 50%; left: -5px; transform: translateY(-50%); cursor: ew-resize; }

                .drag-handle {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 24px;
                    cursor: move;
                    background: transparent;
                }

                :host([locked]) .drag-handle {
                    cursor: not-allowed;
                }
            </style>
            <div class="element-container">
                <div class="drag-handle"></div>
                <div class="content">
                    <slot></slot>
                </div>
                <div class="resize-handles">
                    <div class="resize-handle nw" data-handle="nw"></div>
                    <div class="resize-handle n" data-handle="n"></div>
                    <div class="resize-handle ne" data-handle="ne"></div>
                    <div class="resize-handle e" data-handle="e"></div>
                    <div class="resize-handle se" data-handle="se"></div>
                    <div class="resize-handle s" data-handle="s"></div>
                    <div class="resize-handle sw" data-handle="sw"></div>
                    <div class="resize-handle w" data-handle="w"></div>
                </div>
            </div>
        `;
    }

    _updatePosition() {
        this.style.left = `${this.x}px`;
        this.style.top = `${this.y}px`;
    }

    _updateSize() {
        this.style.width = `${this.width}px`;
        this.style.height = `${this.height}px`;
    }

    _updateSelection() {
        // Visual update handled by CSS :host([selected])
    }

    _bindEvents() {
        this._onMouseDown = this._handleMouseDown.bind(this);
        this._onMouseMove = this._handleMouseMove.bind(this);
        this._onMouseUp = this._handleMouseUp.bind(this);
        this._onClick = this._handleClick.bind(this);

        this.shadowRoot.addEventListener('mousedown', this._onMouseDown);
        document.addEventListener('mousemove', this._onMouseMove);
        document.addEventListener('mouseup', this._onMouseUp);
        this.addEventListener('click', this._onClick);
    }

    _unbindEvents() {
        this.shadowRoot.removeEventListener('mousedown', this._onMouseDown);
        document.removeEventListener('mousemove', this._onMouseMove);
        document.removeEventListener('mouseup', this._onMouseUp);
        this.removeEventListener('click', this._onClick);
    }

    _handleClick(e) {
        if (this.locked) return;

        // Toggle selection
        this.selected = true;
        this.dispatchEvent(
            new CustomEvent('ax-element-select', {
                bubbles: true,
                composed: true,
                detail: { elementId: this.elementId, selected: true },
            })
        );
    }

    _handleMouseDown(e) {
        if (this.locked) return;

        const handle = e.target.closest('.resize-handle');
        const dragHandle = e.target.closest('.drag-handle');

        if (handle && this.resizable) {
            // Start resize
            this._isResizing = true;
            this._resizeHandle = handle.dataset.handle;
            this._startPos = { x: e.clientX, y: e.clientY };
            this._startSize = { width: this.width, height: this.height };
            this._startCoords = { x: this.x, y: this.y };
            e.preventDefault();
            e.stopPropagation();
        } else if (dragHandle && this.isDraggable) {
            // Start drag
            this._isDragging = true;
            this._startPos = { x: e.clientX, y: e.clientY };
            this._startCoords = { x: this.x, y: this.y };
            e.preventDefault();
            e.stopPropagation();
        }
    }

    _handleMouseMove(e) {
        if (this._isDragging) {
            const dx = e.clientX - this._startPos.x;
            const dy = e.clientY - this._startPos.y;

            this.x = this._startCoords.x + dx;
            this.y = this._startCoords.y + dy;
            this._updatePosition();
        } else if (this._isResizing) {
            this._handleResize(e);
        }
    }

    _handleResize(e) {
        const dx = e.clientX - this._startPos.x;
        const dy = e.clientY - this._startPos.y;
        const handle = this._resizeHandle;
        const minSize = 50;

        let newWidth = this._startSize.width;
        let newHeight = this._startSize.height;
        let newX = this._startCoords.x;
        let newY = this._startCoords.y;

        // Handle horizontal resize
        if (handle.includes('e')) {
            newWidth = Math.max(minSize, this._startSize.width + dx);
        } else if (handle.includes('w')) {
            newWidth = Math.max(minSize, this._startSize.width - dx);
            newX = this._startCoords.x + (this._startSize.width - newWidth);
        }

        // Handle vertical resize
        if (handle.includes('s')) {
            newHeight = Math.max(minSize, this._startSize.height + dy);
        } else if (handle.includes('n')) {
            newHeight = Math.max(minSize, this._startSize.height - dy);
            newY = this._startCoords.y + (this._startSize.height - newHeight);
        }

        this.width = newWidth;
        this.height = newHeight;
        this.x = newX;
        this.y = newY;

        this._updatePosition();
        this._updateSize();
    }

    _handleMouseUp() {
        if (this._isDragging) {
            this._isDragging = false;
            this.dispatchEvent(
                new CustomEvent('ax-element-move', {
                    bubbles: true,
                    composed: true,
                    detail: { elementId: this.elementId, x: this.x, y: this.y },
                })
            );
        }

        if (this._isResizing) {
            this._isResizing = false;
            this.dispatchEvent(
                new CustomEvent('ax-element-resize', {
                    bubbles: true,
                    composed: true,
                    detail: { elementId: this.elementId, width: this.width, height: this.height, x: this.x, y: this.y },
                })
            );
        }

        this._startPos = null;
        this._startSize = null;
        this._startCoords = null;
        this._resizeHandle = null;
    }
}

customElements.define('ax-canvas-element', AxCanvasElement);

export default AxCanvasElement;
