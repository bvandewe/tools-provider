/**
 * Canvas Manager
 * Manages viewport transformations (pan/zoom) for canvas elements.
 *
 * Features:
 * - Pan with mouse drag or touch
 * - Zoom with wheel or pinch
 * - Coordinate system conversion (screen ↔ world)
 * - Zoom limits and smooth animations
 * - Keyboard shortcuts
 *
 * Usage:
 *   const manager = new CanvasManager(containerElement);
 *   manager.on('viewportChange', (transform) => { ... });
 */

export class CanvasManager extends EventTarget {
    constructor(container, options = {}) {
        super();

        this.container = container;
        this.options = {
            minZoom: options.minZoom ?? 0.1,
            maxZoom: options.maxZoom ?? 5,
            zoomStep: options.zoomStep ?? 0.1,
            panEnabled: options.panEnabled ?? true,
            zoomEnabled: options.zoomEnabled ?? true,
            ...options,
        };

        // Transform state
        this._transform = {
            x: 0, // Pan X offset
            y: 0, // Pan Y offset
            scale: 1, // Zoom level
        };

        // Interaction state
        this._isPanning = false;
        this._lastPointer = null;
        this._touchDistance = null;

        this._init();
    }

    // =========================================================================
    // Public API
    // =========================================================================

    get transform() {
        return { ...this._transform };
    }

    get scale() {
        return this._transform.scale;
    }

    /**
     * Pan the viewport by delta pixels
     */
    pan(dx, dy) {
        this._transform.x += dx;
        this._transform.y += dy;
        this._applyTransform();
        this._emitChange();
    }

    /**
     * Pan to specific position
     */
    panTo(x, y, animate = false) {
        if (animate) {
            this._animateTo({ x, y, scale: this._transform.scale });
        } else {
            this._transform.x = x;
            this._transform.y = y;
            this._applyTransform();
            this._emitChange();
        }
    }

    /**
     * Zoom by factor around center point
     */
    zoom(factor, centerX = null, centerY = null) {
        const rect = this.container.getBoundingClientRect();
        const cx = centerX ?? rect.width / 2;
        const cy = centerY ?? rect.height / 2;

        const newScale = this._clampScale(this._transform.scale * factor);
        const scaleDiff = newScale / this._transform.scale;

        // Adjust pan to zoom around center point
        this._transform.x = cx - (cx - this._transform.x) * scaleDiff;
        this._transform.y = cy - (cy - this._transform.y) * scaleDiff;
        this._transform.scale = newScale;

        this._applyTransform();
        this._emitChange();
    }

    /**
     * Zoom to specific level
     */
    zoomTo(scale, animate = false) {
        const newScale = this._clampScale(scale);
        if (animate) {
            this._animateTo({ ...this._transform, scale: newScale });
        } else {
            const rect = this.container.getBoundingClientRect();
            const cx = rect.width / 2;
            const cy = rect.height / 2;
            const scaleDiff = newScale / this._transform.scale;

            this._transform.x = cx - (cx - this._transform.x) * scaleDiff;
            this._transform.y = cy - (cy - this._transform.y) * scaleDiff;
            this._transform.scale = newScale;

            this._applyTransform();
            this._emitChange();
        }
    }

    /**
     * Reset to default view
     */
    reset(animate = false) {
        if (animate) {
            this._animateTo({ x: 0, y: 0, scale: 1 });
        } else {
            this._transform = { x: 0, y: 0, scale: 1 };
            this._applyTransform();
            this._emitChange();
        }
    }

    /**
     * Fit content to viewport
     */
    fitToContent(contentBounds, padding = 50) {
        const rect = this.container.getBoundingClientRect();
        const scaleX = (rect.width - padding * 2) / contentBounds.width;
        const scaleY = (rect.height - padding * 2) / contentBounds.height;
        const scale = this._clampScale(Math.min(scaleX, scaleY));

        const x = (rect.width - contentBounds.width * scale) / 2 - contentBounds.x * scale;
        const y = (rect.height - contentBounds.height * scale) / 2 - contentBounds.y * scale;

        this._animateTo({ x, y, scale });
    }

    /**
     * Convert screen coordinates to world coordinates
     */
    screenToWorld(screenX, screenY) {
        return {
            x: (screenX - this._transform.x) / this._transform.scale,
            y: (screenY - this._transform.y) / this._transform.scale,
        };
    }

    /**
     * Convert world coordinates to screen coordinates
     */
    worldToScreen(worldX, worldY) {
        return {
            x: worldX * this._transform.scale + this._transform.x,
            y: worldY * this._transform.scale + this._transform.y,
        };
    }

    /**
     * Destroy and cleanup
     */
    destroy() {
        this._removeListeners();
    }

    // =========================================================================
    // Private Methods
    // =========================================================================

    _init() {
        this._setupListeners();
        this._applyTransform();
    }

    _setupListeners() {
        // Mouse events
        this._onMouseDown = this._handleMouseDown.bind(this);
        this._onMouseMove = this._handleMouseMove.bind(this);
        this._onMouseUp = this._handleMouseUp.bind(this);
        this._onWheel = this._handleWheel.bind(this);

        // Touch events
        this._onTouchStart = this._handleTouchStart.bind(this);
        this._onTouchMove = this._handleTouchMove.bind(this);
        this._onTouchEnd = this._handleTouchEnd.bind(this);

        // Keyboard events
        this._onKeyDown = this._handleKeyDown.bind(this);

        this.container.addEventListener('mousedown', this._onMouseDown);
        this.container.addEventListener('wheel', this._onWheel, { passive: false });
        this.container.addEventListener('touchstart', this._onTouchStart, { passive: false });
        this.container.addEventListener('touchmove', this._onTouchMove, { passive: false });
        this.container.addEventListener('touchend', this._onTouchEnd);
        document.addEventListener('mousemove', this._onMouseMove);
        document.addEventListener('mouseup', this._onMouseUp);
        this.container.addEventListener('keydown', this._onKeyDown);

        // Make container focusable for keyboard events
        if (!this.container.hasAttribute('tabindex')) {
            this.container.setAttribute('tabindex', '0');
        }
    }

    _removeListeners() {
        this.container.removeEventListener('mousedown', this._onMouseDown);
        this.container.removeEventListener('wheel', this._onWheel);
        this.container.removeEventListener('touchstart', this._onTouchStart);
        this.container.removeEventListener('touchmove', this._onTouchMove);
        this.container.removeEventListener('touchend', this._onTouchEnd);
        document.removeEventListener('mousemove', this._onMouseMove);
        document.removeEventListener('mouseup', this._onMouseUp);
        this.container.removeEventListener('keydown', this._onKeyDown);
    }

    _handleMouseDown(e) {
        if (!this.options.panEnabled) return;
        if (e.button !== 0 && e.button !== 1) return; // Left or middle button

        this._isPanning = true;
        this._lastPointer = { x: e.clientX, y: e.clientY };
        this.container.style.cursor = 'grabbing';
        e.preventDefault();
    }

    _handleMouseMove(e) {
        if (!this._isPanning || !this._lastPointer) return;

        const dx = e.clientX - this._lastPointer.x;
        const dy = e.clientY - this._lastPointer.y;

        this.pan(dx, dy);
        this._lastPointer = { x: e.clientX, y: e.clientY };
    }

    _handleMouseUp() {
        this._isPanning = false;
        this._lastPointer = null;
        this.container.style.cursor = '';
    }

    _handleWheel(e) {
        if (!this.options.zoomEnabled) return;
        e.preventDefault();

        const rect = this.container.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const factor = e.deltaY < 0 ? 1 + this.options.zoomStep : 1 - this.options.zoomStep;
        this.zoom(factor, x, y);
    }

    _handleTouchStart(e) {
        if (e.touches.length === 2) {
            // Pinch zoom start
            this._touchDistance = this._getTouchDistance(e.touches);
            e.preventDefault();
        } else if (e.touches.length === 1 && this.options.panEnabled) {
            // Pan start
            this._isPanning = true;
            this._lastPointer = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
    }

    _handleTouchMove(e) {
        if (e.touches.length === 2 && this._touchDistance !== null) {
            // Pinch zoom
            const newDistance = this._getTouchDistance(e.touches);
            const factor = newDistance / this._touchDistance;

            const rect = this.container.getBoundingClientRect();
            const cx = (e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left;
            const cy = (e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top;

            this.zoom(factor, cx, cy);
            this._touchDistance = newDistance;
            e.preventDefault();
        } else if (e.touches.length === 1 && this._isPanning) {
            // Pan
            const dx = e.touches[0].clientX - this._lastPointer.x;
            const dy = e.touches[0].clientY - this._lastPointer.y;

            this.pan(dx, dy);
            this._lastPointer = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
    }

    _handleTouchEnd() {
        this._isPanning = false;
        this._lastPointer = null;
        this._touchDistance = null;
    }

    _handleKeyDown(e) {
        const step = 50;
        switch (e.key) {
            case 'ArrowUp':
                this.pan(0, step);
                e.preventDefault();
                break;
            case 'ArrowDown':
                this.pan(0, -step);
                e.preventDefault();
                break;
            case 'ArrowLeft':
                this.pan(step, 0);
                e.preventDefault();
                break;
            case 'ArrowRight':
                this.pan(-step, 0);
                e.preventDefault();
                break;
            case '+':
            case '=':
                this.zoom(1 + this.options.zoomStep);
                e.preventDefault();
                break;
            case '-':
                this.zoom(1 - this.options.zoomStep);
                e.preventDefault();
                break;
            case '0':
                this.reset(true);
                e.preventDefault();
                break;
        }
    }

    _getTouchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    _clampScale(scale) {
        return Math.max(this.options.minZoom, Math.min(this.options.maxZoom, scale));
    }

    _applyTransform() {
        // Find the content element to transform
        const content = this.container.querySelector('.canvas-content');
        if (content) {
            content.style.transform = `translate(${this._transform.x}px, ${this._transform.y}px) scale(${this._transform.scale})`;
            content.style.transformOrigin = '0 0';
        }
    }

    _animateTo(target, duration = 300) {
        const start = { ...this._transform };
        const startTime = performance.now();

        const animate = time => {
            const elapsed = time - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = this._easeOutCubic(progress);

            this._transform.x = start.x + (target.x - start.x) * eased;
            this._transform.y = start.y + (target.y - start.y) * eased;
            this._transform.scale = start.scale + (target.scale - start.scale) * eased;

            this._applyTransform();

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                this._emitChange();
            }
        };

        requestAnimationFrame(animate);
    }

    _easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    _emitChange() {
        this.dispatchEvent(
            new CustomEvent('viewportChange', {
                detail: this.transform,
            })
        );
    }
}

export default CanvasManager;
